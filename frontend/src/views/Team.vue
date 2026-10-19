<template>
  <el-card>
    <template #header>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <span>团队成员（含贡献统计与时间追溯）</span>
        <el-button type="primary" @click="addVisible=true">新增成员</el-button>
      </div>
    </template>
    <el-table :data="users">
      <el-table-column prop="username" label="账号" width="110" />
      <el-table-column prop="display_name" label="姓名" width="100" />
      <el-table-column label="角色" width="90">
        <template #default="{ row }"><el-tag size="small" :type="row.role==='admin'?'danger':'info'">{{ row.role==='admin'?'管理员':'成员' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }"><el-tag size="small" :type="row.is_active?'success':'danger'">{{ row.is_active?'启用':'停用' }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="created_at" label="加入时间" width="150" />
      <el-table-column prop="last_login_at" label="最近登录" width="150" />
      <el-table-column prop="sop_count" label="SOP数" width="70" />
      <el-table-column prop="fault_count" label="故障数" width="70" />
      <el-table-column prop="script_count" label="脚本数" width="70" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link size="small" @click="resetPwd(row)">重置密码</el-button>
          <el-button link size="small" :type="row.is_active?'danger':'success'" @click="toggle(row)" :disabled="row.username==='admin'">
            {{ row.is_active ? '停用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
  <el-dialog v-model="addVisible" title="新增团队成员" width="420px">
    <el-form label-width="80px">
      <el-form-item label="账号"><el-input v-model="addForm.username" /></el-form-item>
      <el-form-item label="姓名"><el-input v-model="addForm.display_name" /></el-form-item>
      <el-form-item label="初始密码"><el-input v-model="addForm.password" show-password placeholder="至少8位" /></el-form-item>
      <el-form-item label="角色">
        <el-select v-model="addForm.role">
          <el-option label="成员" value="member" /><el-option label="管理员" value="admin" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer><el-button type="primary" @click="addUser">创建</el-button></template>
  </el-dialog>
  <el-dialog v-model="pwdVisible" :title="'重置密码：' + pwdForm.username" width="420px">
    <el-input v-model="pwdForm.new_password" show-password placeholder="新密码（至少8位）" />
    <template #footer><el-button type="primary" @click="doReset">确认重置</el-button></template>
  </el-dialog>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'
const users = ref([])
const addVisible = ref(false)
const addForm = reactive({ username: '', display_name: '', password: '', role: 'member' })
const pwdVisible = ref(false)
const pwdForm = reactive({ id: null, username: '', new_password: '' })
async function load() { users.value = await api.get('/users') }
async function addUser() {
  await api.post('/users', addForm)
  ElMessage.success('成员已创建')
  addVisible.value = false
  Object.assign(addForm, { username: '', display_name: '', password: '', role: 'member' })
  load()
}
function resetPwd(row) { pwdForm.id = row.id; pwdForm.username = row.username; pwdForm.new_password = ''; pwdVisible.value = true }
async function doReset() {
  await api.post(`/users/${pwdForm.id}/reset_password`, { new_password: pwdForm.new_password })
  ElMessage.success('密码已重置')
  pwdVisible.value = false
}
async function toggle(row) {
  await ElMessageBox.confirm(`确认${row.is_active ? '停用' : '启用'}账号 ${row.username}？`, '提示')
  await api.post(`/users/${row.id}/toggle`)
  ElMessage.success('已更新')
  load()
}
onMounted(load)
</script>
