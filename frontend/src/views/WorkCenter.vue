<template>
  <el-card>
    <el-tabs v-model="tab">
      <!-- ========== Tab1: 待审批文档（管理员） ========== -->
      <el-tab-pane v-if="isAdmin" :label="`待审批文档（${docs.length}）`" name="docs">
        <el-table :data="docs" size="small">
          <el-table-column prop="title" label="文档标题" width="240" show-overflow-tooltip />
          <el-table-column prop="created_by" label="上传人" width="100" />
          <el-table-column prop="created_at" label="上传时间" width="150" />
          <el-table-column prop="content" label="内容预览" show-overflow-tooltip />
          <el-table-column label="操作" width="170">
            <template #default="{ row }">
              <el-button size="small" type="success" @click="reviewDoc(row.id, 'approve')">通过</el-button>
              <el-button size="small" type="danger" @click="reviewDoc(row.id, 'reject')">驳回</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!docs.length" description="暂无待审批文档" />
      </el-tab-pane>
      <!-- ========== Tab2: 知识空白录用（管理员） ========== -->
      <el-tab-pane v-if="isAdmin" :label="`知识空白录用（${gaps.length}）`" name="gaps">
        <el-alert type="info" :closable="false"
          title="AI 知识问答未命中本地知识库时，用户选择录入的 AI 答案在此审批。通过后自动向量化入库。" style="margin-bottom:10px" />
        <el-table :data="gaps" size="small">
          <el-table-column prop="question" label="用户问题" width="240" show-overflow-tooltip />
          <el-table-column prop="ai_draft" label="AI 答案" show-overflow-tooltip />
          <el-table-column prop="created_by" label="提交人" width="90" />
          <el-table-column prop="created_at" label="时间" width="150" />
          <el-table-column label="操作" width="190">
            <template #default="{ row }">
              <el-button size="small" type="success" @click="reviewGap(row.id, 'approve')">通过并录入</el-button>
              <el-button size="small" type="danger" @click="reviewGap(row.id, 'reject')">驳回</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!gaps.length" description="暂无待录用内容" />
      </el-tab-pane>
      <!-- ========== Tab3: 故障工单（全员） ========== -->
      <el-tab-pane label="故障工单" name="tickets">
        <el-row :gutter="16">
          <el-col :span="10">
            <el-card class="fill-card">
              <template #header>故障录入（只填现象）</template>
              <el-input v-model="form.phenomenon" type="textarea" :rows="5"
                        placeholder="一句话描述故障现象，例如：线上服务间歇性 502，重启后恢复" />
              <el-button type="primary" style="margin-top:12px;width:100%" @click="submit">提交录入</el-button>
              <div class="tip">提交后进入下方工单池，可流转补充方案与处理人</div>
            </el-card>
          </el-col>
          <el-col :span="14">
            <el-card class="fill-card">
              <template #header>相似故障语义检索</template>
              <div class="search-bar">
                <el-input v-model="searchText" placeholder="描述当前故障现象" @keyup.enter="search" />
                <el-button type="primary" @click="search">检索</el-button>
              </div>
              <div class="result-scroll">
                <el-timeline v-if="results.length">
                  <el-timeline-item v-for="r in results" :key="r.id" :timestamp="r.created_at">
                    <el-card shadow="hover" size="small">
                      <div><b>现象：</b>{{ r.phenomenon }}</div>
                      <div><b>根因：</b>{{ r.root_cause || '未记录' }}</div>
                      <div><b>方案：</b>{{ r.solution }}</div>
                      <div style="margin-top:6px">
                        <el-tag size="small" type="danger">发生 {{ r.occurrence_count }} 次</el-tag>
                        <el-tag size="small">相似 {{ (r.similarity*100).toFixed(1) }}%</el-tag>
                        <el-button link size="small" @click="reoccur(r.id)">+1 又发生了</el-button>
                      </div>
                    </el-card>
                  </el-timeline-item>
                </el-timeline>
                <el-empty v-else description="输入现象后检索" />
              </div>
            </el-card>
          </el-col>
        </el-row>
        <el-card style="margin-top:16px">
          <template #header>故障工单池</template>
          <el-table :data="tickets" size="small" max-height="480">
            <el-table-column prop="phenomenon" label="现象" min-width="220" show-overflow-tooltip />
            <el-table-column prop="solution" label="方案" min-width="200" show-overflow-tooltip />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status==='closed'?'success':row.status==='processing'?'primary':'warning'">
                  {{ {open:'待处理',processing:'处理中',closed:'已关闭'}[row.status] }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="handler" label="处理人" width="90" />
            <el-table-column prop="created_by" label="录入人" width="90" />
            <el-table-column prop="created_at" label="录入时间" width="150" />
            <el-table-column label="操作" width="90">
              <template #default="{ row }">
                <el-button link size="small" type="primary" @click="openUpdate(row)">流转</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
    <el-dialog v-model="updateVisible" title="工单流转（补充方案/处理人）" width="420px">
      <el-form label-width="80px">
        <el-form-item label="状态">
          <el-select v-model="updateForm.status">
            <el-option label="待处理" value="open" />
            <el-option label="处理中" value="processing" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理人"><el-input v-model="updateForm.handler" /></el-form-item>
        <el-form-item label="补充方案"><el-input v-model="updateForm.solution" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button type="primary" @click="doUpdate">保存</el-button></template>
    </el-dialog>
  </el-card>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
const isAdmin = localStorage.getItem('role') === 'admin'
const tab = ref(isAdmin ? 'docs' : 'tickets')   // 管理员默认看审批，成员默认看工单
// ===== 审批：文档 =====
const docs = ref([])
const gaps = ref([])
async function loadApprovals() {
  docs.value = await api.get('/approval/docs', { params: { status: 'pending' } })
  gaps.value = await api.get('/approval/gaps', { params: { status: 'pending' } })
}
async function reviewDoc(id, action) {
  if (action === 'reject') {
    const { value } = await ElMessageBox.prompt('驳回原因', '驳回确认')
    await api.post(`/approval/docs/${id}`, { action, reason: value })
  } else {
    await api.post(`/approval/docs/${id}`, { action })
  }
  ElMessage.success(action === 'approve' ? '已通过，可在 AI 知识问答中检索' : '已驳回')
  loadApprovals()
}
async function reviewGap(id, action) {
  await api.post(`/approval/gaps/${id}`, { action })
  ElMessage.success(action === 'approve' ? '已录用并自动入库' : '已驳回')
  loadApprovals()
}
// ===== 工单：录入 / 检索 / 分析 / 流转 =====
const form = reactive({ phenomenon: '' })
const searchText = ref('')
const results = ref([])
const tickets = ref([])
const updateVisible = ref(false)
const updateForm = reactive({ id: null, status: 'open', handler: '', solution: '' })
async function submit() {
  if (!form.phenomenon.trim()) return ElMessage.warning('请描述故障现象')
  await api.post('/fault/record', { phenomenon: form.phenomenon })
  ElMessage.success('已录入工单池')
  form.phenomenon = ''
  loadTickets()
}
async function search() {
  if (!searchText.value.trim()) return
  results.value = await api.post('/fault/search', { query: searchText.value })
}
async function reoccur(id) {
  await api.post(`/fault/${id}/reoccur`)
  ElMessage.success('已累计发生次数')
  search(); loadTickets()
}
async function loadTickets() {
  tickets.value = await api.get('/fault/list')
}
function openUpdate(row) {
  updateForm.id = row.id
  updateForm.status = row.status
  updateForm.handler = row.handler
  updateForm.solution = ''
  updateVisible.value = true
}
async function doUpdate() {
  await api.post(`/fault/${updateForm.id}/update`, updateForm)
  ElMessage.success('已流转')
  updateVisible.value = false
  loadTickets()
}
onMounted(() => {
  if (isAdmin) loadApprovals()
  loadTickets()
})
</script>
<style scoped>
.search-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.fill-card { height: 100%; }
.tip { color: #64748b; font-size: 12px; margin-top: 10px; text-align: center; }
.result-scroll { max-height: 46vh; overflow-y: auto; padding-right: 4px; }
</style>
