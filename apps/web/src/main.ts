import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import motion from './plugins/motion'
import './assets/main.css'

createApp(App).use(createPinia()).use(router).use(motion).mount('#app')
