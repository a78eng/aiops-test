<template>
  <router-view v-if="$route.path === '/login'" />
  <el-container v-else class="layout">
    <el-aside width="216px" class="aside">
      <div class="logo">
        <div class="logo-icon"><el-icon :size="20"><Cpu /></el-icon></div>
        <div class="logo-text">
          <span class="logo-name">轻量 AIOps</span>
          <span class="logo-sub">智能运维平台</span>
        </div>
      </div>
      <el-menu :default-active="$route.path" router class="menu"
               text-color="#334155" active-text-color="#6366f1">
        <el-menu-item index="/dashboard"><el-icon><Monitor /></el-icon>监控仪表盘</el-menu-item>
        <el-menu-item index="/report"><el-icon><DataAnalysis /></el-icon>智能分析中心</el-menu-item>
        <el-menu-item index="/sop"><el-icon><Folder /></el-icon>SOP 知识库</el-menu-item>
        <el-menu-item index="/rag"><el-icon><ChatDotRound /></el-icon>AI 知识问答</el-menu-item>
        <el-menu-item index="/work"><el-icon><Checked /></el-icon>处理中心</el-menu-item>
        <el-menu-item index="/scripts"><el-icon><Document /></el-icon>脚本模板</el-menu-item>
        <el-menu-item v-if="isAdmin" index="/team"><el-icon><User /></el-icon>团队管理</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container class="right">
      <el-header class="header">
        <span class="page-title">{{ $route.meta.title }}</span>
        <div class="header-right">
          <el-tag size="small" effect="plain" round class="user-tag">{{ userName }}（{{ roleName }}）</el-tag>
          <el-button link type="danger" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main"><router-view /></el-main>
    </el-container>
  </el-container>
</template>
<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Monitor, DataAnalysis, Folder, ChatDotRound, Checked, Document, User, Cpu } from '@element-plus/icons-vue'
const router = useRouter()
const userName = ref(localStorage.getItem('display_name') || localStorage.getItem('username') || '')
const roleName = computed(() => localStorage.getItem('role') === 'admin' ? '管理员' : '成员')
const isAdmin = computed(() => localStorage.getItem('role') === 'admin')
function logout() {
  localStorage.clear()
  router.push('/login')
}
</script>
<style scoped>
.layout { height: 100vh; background: transparent; }

/* ===== 侧边栏：毛玻璃 ===== */
.aside {
  background: rgba(255, 255, 255, 0.38);
  backdrop-filter: blur(22px) saturate(160%);
  -webkit-backdrop-filter: blur(22px) saturate(160%);
  border-right: 1px solid rgba(255, 255, 255, 0.55);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 20px 18px;
}
.logo-icon {
  width: 40px; height: 40px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
  background: linear-gradient(135deg, #6366f1, #a855f7);
  border-radius: 12px;
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
}
.logo-text { display: flex; flex-direction: column; line-height: 1.2; }
.logo-name { font-size: 17px; font-weight: 700; color: #1e293b; }
.logo-sub { font-size: 11px; color: #64748b; letter-spacing: 1px; }

.menu {
  flex: 1;
  background: transparent !important;
  border-right: none !important;
  padding: 0 10px;
}
.menu :deep(.el-menu-item) {
  height: 46px;
  line-height: 46px;
  border-radius: 12px;
  margin: 4px 0;
  font-weight: 500;
}
.menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.5) !important;
}
.menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.16), rgba(168, 85, 247, 0.16)) !important;
  font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.25);
}

/* ===== 顶栏：毛玻璃 ===== */
.right { background: transparent; }
.header {
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(18px) saturate(160%);
  -webkit-backdrop-filter: blur(18px) saturate(160%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.5);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
}
.page-title { font-size: 18px; font-weight: 700; color: #1e293b; }
.header-right { display: flex; align-items: center; gap: 12px; }
.user-tag { background: rgba(255, 255, 255, 0.5); border-color: rgba(99, 102, 241, 0.3); color: #4f46e5; }

/* ===== 内容区 ===== */
.main {
  background: transparent;
  padding: 22px;
  overflow-y: auto;
}
</style>
