<template>
  <el-row :gutter="16">
    <el-col :span="9">
      <el-card>
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span>脚本模板库</span>
            <div>
              <el-button link type="primary" @click="aiVisible=true">AI 生成</el-button>
              <el-button v-if="isAdmin" link type="primary" @click="openCreate">新增模板</el-button>
            </div>
          </div>
        </template>
        <el-input v-model="kw" placeholder="搜索名称/分类" clearable style="margin-bottom:10px" />
        <div v-for="s in filtered" :key="s.id" class="tpl-item" :class="{active: current?.id===s.id}" @click="select(s)">
          <div><b>{{ s.name }}</b><el-tag size="small" style="margin-left:6px">{{ s.category }}</el-tag></div>
          <small style="color:#909399">{{ s.description }} ｜ 使用 {{ s.usage_count }} 次</small>
        </div>
      </el-card>
    </el-col>
    <el-col :span="15">
      <el-card v-if="current">
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span>{{ current.name }}（{{ current.category }}）</span>
            <div>
              <el-button link size="small" type="primary" @click="copyText(current.content, '模板内容')">复制</el-button>
              <template v-if="isAdmin">
                <el-button link size="small" type="warning" @click="openEdit(current)">编辑</el-button>
                <el-button link size="small" type="danger" @click="delScript(current)">删除</el-button>
              </template>
            </div>
          </div>
        </template>
        <el-alert type="info" :closable="false" :title="'创建人：' + current.created_by + ' ｜ 使用 ' + current.usage_count + ' 次'" style="margin-bottom:10px" />
        <pre class="code-block">{{ current.content }}</pre>
        <el-divider>填写变量 → 渲染可执行脚本</el-divider>
        <el-form label-width="120px">
          <el-form-item v-for="p in current.params" :key="p" :label="p">
            <el-input v-model="renderParams[p]" :placeholder="'填写 ' + p" />
          </el-form-item>
        </el-form>
        <el-button type="primary" @click="render">渲染脚本</el-button>
        <div v-if="rendered" style="margin-top:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <span style="font-weight:600;color:#1e293b">渲染结果</span>
            <el-button link size="small" type="primary" @click="copyText(rendered, '渲染脚本')">复制</el-button>
          </div>
          <pre class="code-block">{{ rendered }}</pre>
        </div>
      </el-card>
      <el-empty v-else description="从左侧选择模板" />
    </el-col>
  </el-row>
  <!-- AI 生成 -->
  <el-dialog v-model="aiVisible" title="AI 生成脚本草稿" width="680px">
    <el-input v-model="aiReq" type="textarea" :rows="4" placeholder="例如：批量检查服务器磁盘使用率超过80%就告警，支持主机列表参数" />
    <div v-if="aiResult" style="margin-top:12px">
      <pre class="code-block">{{ aiResult }}</pre>
    </div>
    <template #footer>
      <el-button @click="aiVisible=false">关闭</el-button>
      <el-button v-if="aiResult" @click="copyText(aiResult, 'AI 脚本')">复制</el-button>
      <el-button v-if="aiResult" type="success" @click="saveAiResult">保存为模板</el-button>
      <el-button type="primary" :loading="aiLoading" @click="aiGen">生成</el-button>
    </template>
  </el-dialog>
  <!-- 新增 / 编辑（同一对话框复用） -->
  <el-dialog v-if="isAdmin" v-model="editVisible" :title="editForm.id ? '编辑模板' : '新增模板'" width="640px">
    <el-form label-width="80px">
      <el-form-item label="名称"><el-input v-model="editForm.name" /></el-form-item>
      <el-form-item label="分类"><el-input v-model="editForm.category" placeholder="如：巡检/数据库/日志" /></el-form-item>
      <el-form-item label="描述"><el-input v-model="editForm.description" /></el-form-item>
      <el-form-item label="参数"><el-input v-model="editForm.paramsText" placeholder="逗号分隔：host,threshold" /></el-form-item>
      <el-form-item label="内容">
        <el-input v-model="editForm.content" type="textarea" :rows="12" placeholder="使用 {{host}} 占位符" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editVisible=false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>
<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
const list = ref([])
const current = ref(null)
const kw = ref('')
const renderParams = reactive({})
const rendered = ref('')
const isAdmin = localStorage.getItem('role') === 'admin'
const aiVisible = ref(false)
const aiReq = ref('')
const aiResult = ref('')
const aiLoading = ref(false)
const editVisible = ref(false)
const saving = ref(false)
const editForm = reactive({ id: null, name: '', category: '通用', description: '', paramsText: '', content: '' })
const filtered = computed(() => list.value.filter(s => !kw.value || s.name.includes(kw.value) || s.category.includes(kw.value)))
async function load() { list.value = await api.get('/scripts') }
async function select(s) {
  current.value = await api.get(`/scripts/${s.id}`)
  rendered.value = ''
  current.value.params.forEach(p => { if (!(p in renderParams)) renderParams[p] = '' })
}
async function render() {
  const res = await api.post(`/scripts/${current.value.id}/render`, { params: renderParams })
  rendered.value = res.script
  current.value.usage_count = res.usage_count
}
async function aiGen() {
  if (!aiReq.value.trim()) return ElMessage.warning('请描述脚本需求')
  aiLoading.value = true
  try {
    const res = await api.post('/scripts/ai/generate', { requirement: aiReq.value })
    aiResult.value = res.script
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally { aiLoading.value = false }
}
// ★ AI 生成的草稿 → 打开「新增模板」对话框并回填内容，保存即入库
function saveAiResult() {
  if (!aiResult.value) return
  Object.assign(editForm, {
    id: null, name: '', category: 'AI 生成',
    description: aiReq.value.slice(0, 80),
    paramsText: '', content: aiResult.value
  })
  aiVisible.value = false
  editVisible.value = true
}
// ★ 复制到剪贴板（含降级方案）
async function copyText(text, label) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`已复制${label}`)
  } catch (e) {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    try {
      document.execCommand('copy')
      ElMessage.success(`已复制${label}`)
    } catch (_) {
      ElMessage.error('复制失败，请手动复制')
    }
    document.body.removeChild(ta)
  }
}
// ★ 新增
function openCreate() {
  Object.assign(editForm, { id: null, name: '', category: '通用', description: '', paramsText: '', content: '' })
  editVisible.value = true
}
// ★ 编辑（回填）
async function openEdit(s) {
  const full = await api.get(`/scripts/${s.id}`)
  Object.assign(editForm, {
    id: full.id, name: full.name, category: full.category,
    description: full.description, content: full.content,
    paramsText: (full.params || []).join(',')
  })
  editVisible.value = true
}
// ★ 保存（新增走 POST，编辑走 PUT）
async function save() {
  if (!editForm.name || !editForm.content) return ElMessage.warning('名称和内容必填')
  saving.value = true
  const payload = {
    name: editForm.name, category: editForm.category, description: editForm.description,
    content: editForm.content,
    params: editForm.paramsText.split(',').map(x => x.trim()).filter(Boolean)
  }
  try {
    if (editForm.id) {
      await api.put(`/scripts/${editForm.id}`, payload)
      ElMessage.success('模板已更新')
    } else {
      await api.post('/scripts', payload)
      ElMessage.success('模板已创建')
    }
    editVisible.value = false
    load()
    if (editForm.id && current.value?.id === editForm.id) select(current.value)
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally { saving.value = false }
}
// ★ 删除
async function delScript(s) {
  await ElMessageBox.confirm(`确认删除模板「${s.name}」？`, '删除确认', { type: 'warning' })
  await api.delete(`/scripts/${s.id}`)
  ElMessage.success('已删除')
  if (current.value?.id === s.id) { current.value = null; rendered.value = '' }
  load()
}
onMounted(load)
</script>
<style scoped>
.tpl-item { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.4); cursor: pointer; border-radius: 8px; margin-bottom: 2px; transition: background 0.2s; }
.tpl-item:hover { background: rgba(255, 255, 255, 0.55); }
.tpl-item.active { background: linear-gradient(135deg, rgba(99,102,241,0.14), rgba(168,85,247,0.14)); border-left: 3px solid #6366f1; }
</style>
