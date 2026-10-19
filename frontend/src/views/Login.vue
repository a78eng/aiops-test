<template>
  <div class="login-page">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
    <el-card class="login-card" shadow="never">
      <div class="brand-icon"><el-icon :size="28"><Cpu /></el-icon></div>
      <h2>轻量 AIOps</h2>
      <p class="subtitle">智能运维分析平台</p>
      <el-form :model="form" @keyup.enter="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" show-password size="large" :prefix-icon="Lock" />
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="handleLogin">登 录</el-button>
      </el-form>
    </el-card>
  </div>
</template>
<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { User, Lock, Cpu } from '@element-plus/icons-vue'
import api from '../api'
const router = useRouter()
const loading = ref(false)
const form = reactive({ username: 'admin', password: '' })
async function handleLogin() {
  loading.value = true
  try {
    const res = await api.post('/auth/login', form)
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('username', res.username)
    localStorage.setItem('display_name', res.display_name)
    localStorage.setItem('role', res.role)
    ElMessage.success(`欢迎，${res.display_name}`)
    router.push('/dashboard')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>
<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(1100px 720px at 10% -10%, rgba(99, 102, 241, 0.6), transparent 60%),
    radial-gradient(1000px 680px at 105% 15%, rgba(168, 85, 247, 0.5), transparent 60%),
    radial-gradient(900px 800px at 50% 115%, rgba(34, 211, 238, 0.45), transparent 60%),
    linear-gradient(160deg, #4f46e5 0%, #7c3aed 50%, #0ea5e9 100%);
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.55;
}
.orb-1 { width: 360px; height: 360px; background: #a855f7; top: -80px; left: -60px; }
.orb-2 { width: 300px; height: 300px; background: #22d3ee; bottom: -60px; right: -40px; }
.orb-3 { width: 240px; height: 240px; background: #f472b6; bottom: 20%; left: 12%; }
.login-card {
  width: 400px;
  padding: 28px 24px 18px;
  text-align: center;
  background: rgba(255, 255, 255, 0.16) !important;
  backdrop-filter: blur(26px) saturate(180%);
  -webkit-backdrop-filter: blur(26px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.28) !important;
  border-radius: 22px !important;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.28) !important;
  position: relative;
  z-index: 2;
}
.brand-icon {
  width: 62px; height: 62px;
  margin: 0 auto 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 30px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  border-radius: 18px;
  box-shadow: 0 10px 24px rgba(99, 102, 241, 0.45);
}
h2 { font-size: 24px; color: #fff; margin-bottom: 4px; letter-spacing: 1px; }
.subtitle { color: rgba(255, 255, 255, 0.85); font-size: 13px; margin-bottom: 24px; letter-spacing: 2px; }
.login-card :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.22) !important;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.28) inset;
}
.login-card :deep(.el-input__inner) { color: #fff; }
.login-card :deep(.el-input__inner::placeholder) { color: rgba(255, 255, 255, 0.7); }
</style>
