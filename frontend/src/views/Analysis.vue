<template>
  <el-tabs v-model="tab">
    <!-- Tab1: 每分钟实时简报 -->
    <el-tab-pane label="实时简报" name="minute">
      <el-card>
        <div class="bar">
          <el-tag type="success">系统每 60 秒自动采集指标+日志生成 · 页面 30 秒自动刷新</el-tag>
          <el-button size="small" :loading="briefLoading" @click="loadBrief">立即刷新</el-button>
        </div>
        <el-empty v-if="!brief" description="暂无简报，等待第一分钟自动生成…" />
        <template v-else>
          <div class="brief-card">
            <div class="brief-time">{{ brief.time }}</div>
            <div class="brief-text">{{ brief.ai_brief }}</div>
          </div>
          <el-collapse style="margin-top:12px">
            <el-collapse-item title="查看原始指标" name="m"><pre class="raw">{{ brief.metrics }}</pre></el-collapse-item>
            <el-collapse-item title="查看错误日志摘要" name="l"><pre class="raw">{{ brief.logs }}</pre></el-collapse-item>
          </el-collapse>
        </template>
      </el-card>
    </el-tab-pane>
    <!-- Tab2: ★ 系统全局巡检（核心改造） -->
    <el-tab-pane label="全局巡检" name="inspect">
      <div class="bar">
        <el-button size="small" @click="loadInspect">刷新数据</el-button>
        <el-button type="primary" size="small" :loading="inspecting" @click="genInspectReport">生成 AI 巡检报告</el-button>
        <el-tag v-if="inspect" type="info">
          {{ inspect.docker.available ? 'Docker ' + inspect.docker.count + ' 容器' : 'Docker 不可用' }}
          ｜
          {{ inspect.k8s.available ? 'K8s ' + inspect.k8s.node_count + ' 节点' : '未部署 K8s' }}
        </el-tag>
      </div>
      <!-- 主机负载 -->
      <el-row :gutter="16" v-if="inspect">
        <el-col :span="6"><el-card><div class="m-lbl">CPU 使用率</div><div class="m-val">{{ inspect.metrics.cpu }}%</div></el-card></el-col>
        <el-col :span="6"><el-card><div class="m-lbl">内存使用率</div><div class="m-val">{{ inspect.metrics.mem }}%</div></el-card></el-col>
        <el-col :span="6"><el-card><div class="m-lbl">磁盘使用率</div><div class="m-val">{{ inspect.metrics.disk }}%</div></el-card></el-col>
        <el-col :span="6"><el-card><div class="m-lbl">GPU 显存</div><div class="m-val" style="font-size:16px">{{ inspect.metrics.gpu }}</div></el-card></el-col>
      </el-row>
      <!-- Docker 业务容器 -->
      <el-card style="margin-top:16px" v-if="inspect && inspect.docker.available">
        <template #header>Docker 容器业务概况（{{ inspect.docker.count }} 个运行中）</template>
        <el-table :data="inspect.docker.containers" size="small" max-height="300">
          <el-table-column prop="name" label="容器名" width="200" />
          <el-table-column prop="image" label="镜像" show-overflow-tooltip />
          <el-table-column prop="status" label="运行状态" width="220" />
        </el-table>
      </el-card>
      <el-card style="margin-top:16px" v-else-if="inspect">
        <el-alert type="info" :closable="false" title="Docker 未部署或不可用" />
      </el-card>
      <!-- K8s 集群（如有） -->
      <el-card style="margin-top:16px" v-if="inspect && inspect.k8s.available">
        <template #header>K8s 集群概况（{{ inspect.k8s.node_count }} 节点 · {{ inspect.k8s.pods_total }} Pod）</template>
        <el-alert v-if="inspect.k8s.issues.length" type="warning" :closable="false"
          title="存在异常 Pod，详见 AI 巡检报告或 kubectl 排查" style="margin-bottom:10px" />
        <div>
          <el-tag v-for="n in inspect.k8s.nodes" :key="n" style="margin:4px">{{ n }}</el-tag>
        </div>
        <el-table :data="inspect.k8s.pods.slice(0, 50)" size="small" max-height="320" style="margin-top:10px">
          <el-table-column prop="namespace" label="命名空间" width="140" />
          <el-table-column prop="name" label="Pod" show-overflow-tooltip />
          <el-table-column prop="ready" label="就绪" width="80" />
          <el-table-column prop="status" label="状态" width="110" />
        </el-table>
      </el-card>
      <el-card style="margin-top:16px" v-else-if="inspect">
        <el-alert type="info" :closable="false"
          title="当前未部署 K8s 集群（Docker 单机架构）。后续部署 K8s 后，本平台自动通过 kubectl 采集展示，无需改造。" />
      </el-card>
      <!-- AI 巡检报告 -->
      <el-card style="margin-top:16px">
        <template #header>AI 全局巡检报告（大模型综合主机 + 容器 + 集群 + 日志）</template>
        <div v-if="inspectReportHtml" class="markdown-body" v-html="inspectReportHtml"></div>
        <el-empty v-else description="点击上方「生成 AI 巡检报告」获取整体健康度分析" />
      </el-card>
    </el-tab-pane>
    <!-- Tab3: 故障统计 -->
    <el-tab-pane label="故障统计" name="faults">
      <el-row :gutter="16">
        <el-col :span="6"><el-card><div class="num">{{ counts.total }}</div><div class="lbl">故障总数</div></el-card></el-col>
        <el-col :span="6"><el-card><div class="num" style="color:#e6a23c">{{ counts.open }}</div><div class="lbl">待处理</div></el-card></el-col>
        <el-col :span="6"><el-card><div class="num" style="color:#409eff">{{ counts.processing }}</div><div class="lbl">处理中</div></el-card></el-col>
        <el-col :span="6"><el-card><div class="num" style="color:#67c23a">{{ counts.closed }}</div><div class="lbl">已关闭</div></el-card></el-col>
      </el-row>
      <el-card style="margin-top:16px">
        <template #header>高频故障 Top10（按发生次数）</template>
        <el-table :data="topFaults" size="small">
          <el-table-column prop="phenomenon" label="故障现象" show-overflow-tooltip />
          <el-table-column prop="occurrence_count" label="发生次数" width="90" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status==='closed'?'success':row.status==='processing'?'primary':'warning'">
                {{ {open:'待处理',processing:'处理中',closed:'已关闭'}[row.status] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_by" label="录入人" width="100" />
        </el-table>
      </el-card>
    </el-tab-pane>
    <!-- Tab4: 处置效率 -->
    <el-tab-pane label="处置效率" name="efficiency">
      <el-card>
        <el-statistic title="已关闭故障平均处置时长" :value="avgHours" :precision="1" suffix="小时" />
        <el-divider />
        <el-table :data="closedFaults" size="small" max-height="480">
          <el-table-column prop="phenomenon" label="故障现象" show-overflow-tooltip />
          <el-table-column prop="handler" label="处理人" width="100" />
          <el-table-column label="处置时长（小时）" width="140">
            <template #default="{ row }">{{ row.duration_h.toFixed(1) }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-tab-pane>
  </el-tabs>
</template>
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import api from '../api'
const tab = ref('inspect')
// ===== 实时简报 =====
const brief = ref(null)
const briefLoading = ref(false)
let briefTimer = null
async function loadBrief() {
  try { brief.value = (await api.get('/report/minute-brief/latest')).brief } catch (e) {}
}
// ===== 全局巡检 =====
const inspect = ref(null)
const inspecting = ref(false)
const inspectReportHtml = ref('')
async function loadInspect() {
  try { inspect.value = await api.get('/monitor/inspect') } catch (e) { ElMessage.error('巡检数据加载失败：' + e.message) }
}
async function genInspectReport() {
  inspecting.value = true
  try {
    const res = await api.post('/monitor/inspect-report', {})
    inspectReportHtml.value = marked(res.report)
    ElMessage.success('AI 巡检报告生成完成')
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally { inspecting.value = false }
}
// ===== 故障统计 =====
const faults = ref([])
async function loadFaults() { try { faults.value = await api.get('/fault/list') } catch (e) {} }
const counts = computed(() => ({
  total: faults.value.length,
  open: faults.value.filter(f => f.status === 'open').length,
  processing: faults.value.filter(f => f.status === 'processing').length,
  closed: faults.value.filter(f => f.status === 'closed').length
}))
const topFaults = computed(() => [...faults.value].sort((a, b) => b.occurrence_count - a.occurrence_count).slice(0, 10))
const closedFaults = computed(() =>
  faults.value.filter(f => f.status === 'closed' && f.closed_at).map(f => {
    return { ...f, duration_h: (new Date(f.closed_at) - new Date(f.created_at)) / 3600000 }
  }).sort((a, b) => b.duration_h - a.duration_h)
)
const avgHours = computed(() => {
  if (!closedFaults.value.length) return 0
  return closedFaults.value.reduce((s, f) => s + f.duration_h, 0) / closedFaults.value.length
})
onMounted(() => {
  loadInspect()
  loadFaults()
  loadBrief()
  briefTimer = setInterval(loadBrief, 30000)
})
onBeforeUnmount(() => clearInterval(briefTimer))
</script>
<style>
.bar { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.brief-card { background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(34,211,238,0.08)); border-radius: 12px; padding: 18px; border: 1px solid rgba(255,255,255,0.5); }
.brief-time { color: #64748b; font-size: 13px; margin-bottom: 8px; }
.brief-text { font-size: 15px; line-height: 1.8; white-space: pre-wrap; word-break: break-word; max-height: 40vh; overflow-y: auto; }
.raw { background: rgba(30,41,59,0.92); color: #e2e8f0; padding: 12px; border-radius: 8px; font-size: 13px; white-space: pre-wrap; word-break: break-all; max-height: 320px; overflow: auto; }
.markdown-body { line-height: 1.8; }
.markdown-body h1, .markdown-body h2, .markdown-body h3 { margin: 14px 0 8px; }
.markdown-body code { background: rgba(99,102,241,0.12); padding: 2px 6px; border-radius: 4px; }
.m-lbl { color: #64748b; font-size: 13px; }
.m-val { font-size: 26px; font-weight: bold; margin-top: 6px; color: #1e293b; }
.num { font-size: 30px; font-weight: bold; text-align: center; color: #1e293b; }
.lbl { text-align: center; color: #64748b; margin-top: 6px; }
</style>
