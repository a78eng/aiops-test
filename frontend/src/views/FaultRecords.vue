<template>
  <el-row :gutter="16">
    <!-- 左侧：录入新故障 -->
    <el-col :span="10">
      <el-card>
        <template #header>录入新故障（入库并向量化，供下次语义检索）</template>
        <el-form :model="form" label-width="80px">
          <el-form-item label="故障现象">
            <el-input v-model="form.phenomenon" type="textarea" :rows="3" placeholder="例如：线上服务间歇性 502，重启后恢复" />
          </el-form-item>
          <el-form-item label="根因分析">
            <el-input v-model="form.root_cause" type="textarea" :rows="3" placeholder="例如：Nginx upstream 连接池耗尽" />
          </el-form-item>
          <el-form-item label="处理步骤">
            <el-input v-model="form.solution" type="textarea" :rows="4" placeholder="例如：1. 调整 keepalive 参数 2. 增加后端节点" />
          </el-form-item>
          <el-button type="primary" @click="submit">提交录入</el-button>
        </el-form>
      </el-card>
    </el-col>

    <!-- 右侧：相似故障语义检索 -->
    <el-col :span="14">
      <el-card>
        <template #header>相似故障检索（向量匹配历史案例，无需精确关键词）</template>
        <div class="search-bar">
          <el-input v-model="searchText" placeholder="描述当前故障现象，自动检索相似历史故障" @keyup.enter="search" />
          <el-button type="primary" @click="search">检索</el-button>
        </div>
        <el-empty v-if="!results.length" description="输入故障现象后检索" />
        <el-timeline v-else>
          <el-timeline-item v-for="r in results" :key="r.id" :timestamp="r.created_at" placement="top">
            <el-card shadow="hover">
              <div><b>现象：</b>{{ r.phenomenon }}</div>
              <div><b>根因：</b>{{ r.root_cause || '未记录' }}</div>
              <div><b>方案：</b>{{ r.solution }}</div>
              <div class="meta">
                <el-tag size="small" type="danger">历史发生 {{ r.occurrence_count }} 次</el-tag>
                <el-tag size="small">相似度 {{ (r.similarity * 100).toFixed(1) }}%</el-tag>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const form = reactive({ phenomenon: '', root_cause: '', solution: '' })
const searchText = ref('')
const results = ref([])

async function submit() {
  if (!form.phenomenon || !form.solution) {
    ElMessage.warning('故障现象和处理步骤必填')
    return
  }
  try {
    await api.post('/fault/record', form)
    ElMessage.success('已录入，向量化完成')
    form.phenomenon = form.root_cause = form.solution = ''
  } catch (e) {
    ElMessage.error('录入失败：' + e.message)
  }
}

async function search() {
  if (!searchText.value.trim()) return
  try {
    const res = await api.post('/fault/search', { query: searchText.value })
    results.value = res
  } catch (e) {
    ElMessage.error('检索失败：' + e.message)
  }
}
</script>

<style scoped>
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; }
.meta { margin-top: 8px; display: flex; gap: 8px; }
</style>
