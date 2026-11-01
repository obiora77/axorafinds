<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { LogOut, Menu, X, LayoutDashboard } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)

const links = [
  { label: 'Home', to: '/' },
  { label: 'Properties', to: '/properties' },
  { label: 'About', to: '/about' },
] as const

watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false
  },
)

async function logout(): Promise<void> {
  auth.logout()
  menuOpen.value = false
  await router.push('/')
}
</script>

<template>
  <header class="on-red sticky top-0 z-40 bg-brand text-white" style="padding-top: env(safe-area-inset-top)">
    <div class="page-wrap flex h-16 items-center justify-between gap-4">
      <RouterLink to="/" class="flex min-h-11 items-center" aria-label="Axora Finds, home">
        <img src="/logo.png" alt="" width="138" height="32" class="h-8 w-auto" />
        <span class="text-xl font-bold tracking-wide">
          AXORA
        </span>
      </RouterLink>

      <nav class="hidden items-center gap-1 md:flex" aria-label="Main">
        <RouterLink v-for="link in links" :key="link.to" :to="link.to" class="nav-link">{{ link.label }}</RouterLink>
        <template v-if="auth.isAuthed">
          <RouterLink v-if="auth.isStaff" to="/admin" class="nav-link gap-2">
            <LayoutDashboard class="size-4" aria-hidden="true" />
            Dashboard
          </RouterLink>
          <RouterLink v-if="auth.isOwner" to="/list-property" class="nav-link">List a property</RouterLink>
          <button type="button" class="nav-link gap-2" @click="logout">
            <LogOut class="size-4" aria-hidden="true" />
            Logout
          </button>
        </template>
        <template v-else>
          <RouterLink to="/login" class="nav-link">Login</RouterLink>
          <RouterLink to="/signup" class="btn btn-light ml-1">Sign Up</RouterLink>
        </template>
      </nav>

      <button
        type="button"
        class="grid size-11 place-items-center rounded-full hover:bg-white/15 md:hidden"
        :aria-expanded="menuOpen"
        aria-controls="mobile-menu"
        :aria-label="menuOpen ? 'Close menu' : 'Open menu'"
        @click="menuOpen = !menuOpen"
      >
        <X v-if="menuOpen" class="size-6" aria-hidden="true" />
        <Menu v-else class="size-6" aria-hidden="true" />
      </button>
    </div>

    <nav v-show="menuOpen" id="mobile-menu" class="border-t border-white/25 md:hidden" aria-label="Main mobile">
      <ul class="page-wrap flex flex-col gap-1 py-3">
        <li v-for="link in links" :key="link.to">
          <RouterLink :to="link.to" class="nav-link w-full">{{ link.label }}</RouterLink>
        </li>
        <template v-if="auth.isAuthed">
          <li v-if="auth.isStaff">
            <RouterLink to="/admin" class="nav-link w-full gap-2">
              <LayoutDashboard class="size-4" aria-hidden="true" />
              Dashboard
            </RouterLink>
          </li>
          <li v-if="auth.isOwner">
            <RouterLink to="/list-property" class="nav-link w-full">List a property</RouterLink>
          </li>
          <li>
            <button type="button" class="nav-link w-full gap-2" @click="logout">
              <LogOut class="size-4" aria-hidden="true" />
              Logout
            </button>
          </li>
        </template>
        <template v-else>
          <li><RouterLink to="/login" class="nav-link w-full">Login</RouterLink></li>
          <li><RouterLink to="/signup" class="btn btn-light w-full">Sign Up</RouterLink></li>
        </template>
      </ul>
    </nav>
  </header>
</template>
