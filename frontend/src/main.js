import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './style.css'   // 全局毛玻璃主题样式（覆盖 Element Plus 卡片/弹窗等）
import zhCn from 'element-plus/es/locale/lang/zh-cn'  // 组件中文语言包
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })   // Element Plus 全量引入，UI 组件库
app.mount('#app')
