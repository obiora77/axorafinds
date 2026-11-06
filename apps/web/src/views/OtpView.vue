<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { parseApiError } from '@/lib/api'
import { safeRedirect } from '@/router'
import { useAuthStore } from '@/stores/auth'

const COOLDOWN_SECONDS = 30

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const email = ref(typeof route.query.email === 'string' ? route.query.email : '')
const code = ref('')
const error = ref('')
const busy = ref(false)
const purpose = computed(() => (route.query.purpose === 'password_reset' ? 'password_reset' : 'signup'))
const title = computed(() => (purpose.value === 'signup' ? 'Verify your email' : 'Verify your reset code'))

// Arriving here from sign-up or login means a code was emailed a moment ago.
const notice = ref(route.query.from === 'login' ? 'Your email is not verified yet. We just sent you a new code.' : '')
const cooldown = ref(0)
let timer: number | undefined

function startCooldown(): void {
  window.clearInterval(timer)
  cooldown.value = COOLDOWN_SECONDS
  timer = window.setInterval(() => {
    cooldown.value -= 1
    if (cooldown.value <= 0) window.clearInterval(timer)
  }, 1000)
}
if (email.value) startCooldown()
onBeforeUnmount(() => window.clearInterval(timer))

function onCodeInput(): void {
  code.value = code.value.replace(/\D/g, '').slice(0, 6)
}

async function submit(): Promise<void> {
  error.value = ''
  notice.value = ''
  busy.value = true
  try {
    await auth.verifyOtp(email.value.trim(), code.value.trim(), purpose.value)
    if (purpose.value === 'signup') {
      // The account is now active and signed in. Owners go to list a property, everyone else to browse.
      const fallback = auth.isOwner ? '/list-property' : '/properties'
      await router.push(safeRedirect(route.query.redirect, fallback))
    } else {
      await router.push({ name: 'reset-password', query: { email: email.value.trim(), step: 'set-password' } })
    }
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    busy.value = false
  }
}

async function resend(): Promise<void> {
  error.value = ''
  notice.value = ''
  busy.value = true
  try {
    await auth.resendOtp(email.value.trim(), purpose.value)
    notice.value = 'If this account is eligible, a new code has been sent. Check your spam folder too.'
    code.value = ''
    startCooldown()
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="page-wrap py-8 sm:py-14" aria-labelledby="otp-title">
    <div class="mx-auto max-w-md rounded-3xl bg-white p-6 sm:p-8">
      <h1 id="otp-title" class="text-3xl font-extrabold">{{ title }}</h1>
      <p class="mt-2 text-muted">
        <template v-if="email">We sent a 6-digit code to <strong class="text-ink">{{ email }}</strong>.</template>
        <template v-else>Enter your email and the 6-digit code we sent you.</template>
        It expires in 10 minutes.
      </p>

      <form class="mt-6 space-y-4" novalidate @submit.prevent="submit">
        <div>
          <label class="label" for="otp-email">Email</label>
          <input id="otp-email" v-model="email" class="input" type="email" inputmode="email" autocomplete="email" required />
        </div>
        <div>
          <label class="label" for="otp-code">6-digit code</label>
          <input
            id="otp-code"
            v-model="code"
            class="input text-center font-display text-2xl tracking-[0.5em]"
            inputmode="numeric"
            autocomplete="one-time-code"
            maxlength="6"
            placeholder="000000"
            required
            @input="onCodeInput"
          />
        </div>

        <p v-if="error" class="rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ error }}</p>
        <p v-if="notice" class="rounded-xl border border-line p-3" role="status">{{ notice }}</p>

        <button class="btn btn-primary w-full" type="submit" :disabled="busy || code.length !== 6 || !email.trim()">
          {{ busy ? 'Verifying...' : 'Verify code' }}
        </button>
      </form>

      <button
        type="button"
        class="mt-4 inline-flex min-h-11 w-full items-center justify-center font-semibold text-brand hover:underline disabled:cursor-not-allowed disabled:opacity-60 disabled:no-underline"
        :disabled="busy || !email.trim() || cooldown > 0"
        @click="resend"
      >
        {{ cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code' }}
      </button>

      <p v-if="purpose === 'signup'" class="text-center text-sm text-muted">
        Wrong email?
        <RouterLink :to="{ name: 'signup' }" class="font-semibold text-brand hover:underline">Start again</RouterLink>
      </p>
    </div>
  </section>
</template>
