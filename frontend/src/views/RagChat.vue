<template>
  <el-card class="chat-card">
    <template #header>AI 知识问答（统一检索 SOP 文档 + 历史故障案例）</template>
    <div class="chat-box" ref="chatBox">
      <div v-for="(msg, i) in messages" :key="i" :class="msg.role === 'user' ? 'msg-user' : 'msg-ai'">
        <div class="bubble" :class="msg.role === 'ai' ? 'bubble-ai' : ''">
          <div v-if="msg.role === 'ai'" class="markdown-body" v-html="msg.html || msg.content"></div>
          <template v-else>{{ msg.content }}</template>
        </div>
        <div v-if="msg.sources?.length" class="sources">
          参考：
          <el-tag v-for="(s, j) in msg.sources" :key="j" size="small" :type="s.type==='sop' ? 'success' : 'warning'">
            {{ s.title }}
          </el-tag>
        </div>
        <!-- 每条 AI 回答都可选择录入知识库（知识空白录用） -->
        <div v-if="msg.record_answer && !msg.recorded" class="record-zone">
          <el-button size="small" type="success" @click="recordToKb(msg)">将此答案录入知识库</el-button>
          <span class="hint">{{ msg.can_record ? '本地知识库未命中，以上为 AI 生成答案' : '确认答案有用可录入，管理员审批后入库' }}</span>
        </div>
        <div v-if="msg.recorded" class="sources">
          <el-tag size="small" type="success">已提交录入审批，通过后自动入库</el-tag>
        </div>
      </div>
      <div v-if="thinking" class="msg-ai"><div class="bubble bubble-ai">正在检索 SOP 与故障案例…</div></div>
    </div>
    <div class="chat-input">
      <el-input v-model="question" placeholder="输入任何运维问题，例如：MySQL 主从延迟怎么处理？" @keyup.enter="ask" />
      <el-button type="primary" :loading="thinking" @click="ask">发送</el-button>
    </div>
  </el-card>
</template>
<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import api from '../api'
const messages = ref([{ role: 'ai', content: '你好！我是 AI 知识问答助手。我会同时检索团队 SOP 文档和历史故障案例来回答；查不到的会由 AI 直接解答，并询问你是否录入知识库。' }])
const question = ref('')
const thinking = ref(false)
const chatBox = ref(null)
async function ask() {
  if (!question.value.trim() || thinking.value) return
  messages.value.push({ role: 'user', content: question.value })
  const q = question.value
  question.value = ''
  thinking.value = true
  scrollToBottom()
  try {
    const res = await api.post('/rag/chat', { question: q })
    messages.value.push({
      role: 'ai',
      content: res.answer,
      html: marked(res.answer),
      sources: res.sources,
      can_record: res.can_record,
      record_question: res.record_question || q,
      record_answer: res.answer,
      recorded: false
    })
  } catch (e) {
    messages.value.push({ role: 'ai', content: '请求失败：' + e.message })
  } finally {
    thinking.value = false
    scrollToBottom()
  }
}
async function recordToKb(msg) {
  try {
    await api.post('/sop/record-gap', { question: msg.record_question, ai_answer: msg.record_answer })
    msg.recorded = true
    ElMessage.success('已提交审批，管理员通过后自动录入知识库')
  } catch (e) {
    ElMessage.error('提交失败：' + (e.response?.data?.detail || e.message))
  }
}
function scrollToBottom() {
  nextTick(() => { chatBox.value && (chatBox.value.scrollTop = chatBox.value.scrollHeight) })
}
</script>
<style scoped>
.chat-card :deep(.el-card__body) { display: flex; flex-direction: column; }
.chat-box {
  height: calc(100vh - 260px);
  min-height: 360px;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 16px;
}
.msg-user { display: flex; justify-content: flex-end; margin: 10px 0; }
.msg-ai { display: flex; justify-content: flex-start; flex-wrap: wrap; margin: 10px 0; }
.bubble {
  max-width: 76%;
  padding: 10px 16px;
  border-radius: 14px;
  line-height: 1.7;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.msg-user .bubble {
  background: linear-gradient(135deg, #6366f1, #818cf8);
  color: #fff;
  white-space: pre-wrap;
  border-bottom-right-radius: 4px;
}
.bubble-ai {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-bottom-left-radius: 4px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.bubble-ai :deep(.markdown-body) { max-height: 50vh; }
.sources { margin: 6px 0 0 4px; font-size: 12px; color: #64748b; display: flex; gap: 4px; align-items: center; flex-wrap: wrap; }
.record-zone { width: 100%; margin: 8px 0 0 4px; display: flex; align-items: center; gap: 10px; }
.hint { font-size: 12px; color: #64748b; }
.chat-input { display: flex; gap: 8px; margin-top: 12px; }
</style>
