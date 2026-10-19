<template>
  <div>
    <el-card>
      <div class="report-header">
        <!-- 按日期查看历史报告 -->
        <el-date-picker v-model="date" type="date" value-format="YYYY-MM-DD" :clearable="false" @change="loadReport" />
        <!-- 手动触发后端调用大模型生成日报 -->
        <el-button type="primary" :loading="generating" @click="generate">
          生成 AI 日报（大模型分析监控+日志）
        </el-button>
      </div>

      <!-- Markdown 渲染大模型返回的报告 -->
      <div v-if="report" class="markdown-body" v-html="reportHtml"></div>
      <el-empty v-else description="当日暂无报告，点击上方按钮生成" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'   // Markdown 转 HTML 渲染
import api from '../api'

const date = ref(new Date().toISOString().slice(0, 10))
const report = ref('')
const generating = ref(false)
const reportHtml = ref('')

async function loadReport() {
  const res = await api.get('/report/detail', { params: { date: date.value } })
  report.value = res.report?.ai_report || ''
  if (report.value) reportHtml.value = marked(report.value)
}

async function generate() {
  generating.value = true
  try {
    // 后端会：拉 Prometheus 指标 → 拉 Loki 错误日志 → 拼 Prompt → 调 Ollama → 存库
    await api.post('/report/generate', { date: date.value })
    ElMessage.success('报告生成完成')
    await loadReport()
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    generating.value = false
  }
}

onMounted(loadReport)
</script>

<style>
.report-header { display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.markdown-body { line-height: 1.8; }
</style>
