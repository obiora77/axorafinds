import { nextTick } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { prefersReducedMotion } from '@/plugins/motion'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    requiresStaff?: boolean
    guestOnly?: boolean
  }
}

/** Only follow redirects that stay on this site. */
export function safeRedirect(value: unknown, fallback = '/'): string {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') ? value : fallback
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: 'Home' } },
    {
      path: '/properties',
      name: 'properties',
      component: () => import('@/views/PropertiesView.vue'),
      meta: { title: 'Properties' },
    },
    {
      path: '/properties/:slug',
      name: 'property',
      component: () => import('@/views/PropertyDetailView.vue'),
      meta: { title: 'Property' },
    },
    {
      path: '/list-property',
      name: 'list-property',
      component: () => import('@/views/ListPropertyView.vue'),
      meta: { title: 'List a property', requiresAuth: true },
    },
    { path: '/about', name: 'about', component: () => import('@/views/AboutView.vue'), meta: { title: 'About' } },
    { path: '/contact', name: 'contact', component: () => import('@/views/ContactView.vue'), meta: { title: 'Contact' } },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminView.vue'),
      meta: { title: 'Staff dashboard', requiresAuth: true, requiresStaff: true },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: 'Login', guestOnly: true },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('@/views/ResetPassword.vue'),
      meta: { title: 'RestPassword', guestOnly: true},
    },
    {
      path: '/otp',
      name: 'otp',
      component: () => import('@/views/OtpView.vue'),
      meta: { title: 'Otp'}
    },
    {
      path: '/signup',
      name: 'signup',
      component: () => import('@/views/SignupView.vue'),
      meta: { title: 'Sign up', guestOnly: true },
    },
    { path: '/legal/:slug', name: 'legal', component: () => import('@/views/LegalView.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.hash) return { el: to.hash, top: 80, behavior: prefersReducedMotion() ? 'auto' : 'smooth' }
    if (to.path === from.path) return false // filter changes keep their scroll position
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.restore()
  if (to.meta.requiresAuth && !auth.isAuthed) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  // Staff pages are also protected from signed-in owners and seekers.
  if (to.meta.requiresStaff && !auth.isStaff) {
    return { name: 'home' }
  }
  if (to.meta.guestOnly && auth.isAuthed) {
    return safeRedirect(to.query.redirect)
  }
  return true
})

let firstNavigation = true
router.afterEach((to) => {
  const page = typeof to.meta.title === 'string' ? to.meta.title : ''
  document.title = page ? `${page} | Axora Finds` : 'Axora Finds | Verified rentals in Nigeria'
  if (firstNavigation) {
    firstNavigation = false
    return
  }
  // Move keyboard and screen-reader focus to the new page content.
  void nextTick(() => document.getElementById('main')?.focus({ preventScroll: true }))
})

export default router
