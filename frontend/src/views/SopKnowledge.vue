<template>
  <el-card>
    <template #header>SOP 文档库（可在线查看 / 编辑 / 删除）</template>
    <el-alert type="info" :closable="false"
      title="上传或编辑后的文档需在「处理中心」由管理员审批；编辑/删除仅管理员或上传者本人可操作。" style="margin-bottom:12px" />
    <el-upload drag :action="'/api/sop/upload'" :headers="uploadHeaders" :on-success="onUploadSuccess" :multiple="false">
      <el-icon style="font-size:36px"><UploadFilled /></el-icon>
      <div>拖拽 .md / .txt 文件上传</div>
    </el-upload>
    <el-divider />
    <el-table :data="docs" size="small" max-height="480">
      <el-table-column prop="title" label="文档名称" show-overflow-tooltip />
      <el-table-column prop="chunk_count" label="分块" width="60" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status==='approved'?'success':row.status==='pending'?'warning':'danger'">
            {{ {approved:'已通过',pending:'待审批',rejected:'已驳回'}[row.status] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_by" label="上传人" width="90" />
      <el-table-column prop="created_at" label="时间" width="150" />
      <el-table-column label="操作" width="210">
        <template #default="{ row }">
          <el-button link size="small" type="primary" @click="viewDoc(row)">查看</el-button>
          <el-button link size="small" type="success" @click="downloadDoc(row)">下载</el-button>
          <el-button link size="small" type="warning" :disabled="!row.can_manage" @click="openEdit(row)">编辑</el-button>
          <el-button link size="small" type="danger" :disabled="!row.can_manage" @click="delDoc(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <!-- 查看原文 -->
    <el-dialog v-model="viewVisible" :title="viewForm.title" width="700px" top="5vh">
      <el-descriptions :column="2" border size="small" style="margin-bottom:10px">
        <el-descriptions-item label="上传人">{{ viewForm.created_by }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ viewForm.created_at }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ viewForm.status }}</el-descriptions-item>
      </el-descriptions>
      <pre class="doc-content">{{ viewForm.content }}</pre>
    </el-dialog>
    <!-- 在线编辑 -->
    <el-dialog v-model="editVisible" title="编辑 SOP 文档（保存后重新进入待审批）" width="800px" top="5vh">
      <el-form label-width="80px">
        <el-form-item label="标题"><el-input v-model="editForm.title" /></el-form-item>
        <el-form-item label="内容">
          <el-input v-model="editForm.content" type="textarea" :rows="20" placeholder="支持 Markdown 文本" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存修改</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '../api'
const docs = ref([])
const uploadHeaders = { Authorization: `Bearer ${localStorage.getItem('token')}` }
const viewVisible = ref(false)
const viewForm = ref({ title: '', content: '', created_by: '', created_at: '', status: '' })
const editVisible = ref(false)
const editForm = ref({ doc_key: '', title: '', content: '' })
const saving = ref(false)
async function loadDocs() {
  docs.value = await api.get('/sop/list')
}
function onUploadSuccess() {
  ElMessage.success('已提交，等待管理员审批后生效')
  loadDocs()
}
// ★ 查看
async function viewDoc(row) {
  const res = await api.get(`/sop/detail/${row.doc_key}`)
  viewForm.value = res
  viewVisible.value = true
}
// ★ 下载文档（Blob 下载，兼容中文文件名）
async function downloadDoc(row) {
  try {
    const blob = await api.get(`/sop/download/${row.doc_key}`, { responseType: 'blob' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = (row.title || `${row.doc_key}.md`).replace(/\.(md|txt)$/i, '') + '.md'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败：' + (e.response?.data?.detail || e.message))
  }
}
// ★ 编辑
function openEdit(row) {
  api.get(`/sop/detail/${row.doc_key}`).then(res => {
    editForm.value = { doc_key: row.doc_key, title: res.title, content: res.content }
    editVisible.value = true
  })
}
async function saveEdit() {
  if (!editForm.value.content.trim()) return ElMessage.warning('内容不能为空')
  saving.value = true
  try {
    await api.put(`/sop/update/${editForm.value.doc_key}`, {
      title: editForm.value.title, content: editForm.value.content
    })
    ElMessage.success('已保存，重新进入待审批，管理员通过后生效')
    editVisible.value = false
    loadDocs()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally { saving.value = false }
}
// ★ 删除
async function delDoc(row) {
  await ElMessageBox.confirm(`确认删除文档「${row.title}」？所有切片将一并删除，不可恢复。`, '删除确认', { type: 'warning' })
  await api.delete(`/sop/doc/${row.doc_key}`)
  ElMessage.success('已删除')
  loadDocs()
}
onMounted(loadDocs)
</script>
<style scoped>
.doc-content { background: #f7f8fa; padding: 14px; border-radius: 6px; max-height: 55vh; overflow: auto; white-space: pre-wrap; line-height: 1.7; font-size: 13px; }
</style>
