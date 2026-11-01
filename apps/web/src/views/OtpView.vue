<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { parseApiError } from '@/lib/api'
import { safeRedirect } from '@/router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const email = ref(typeof route.query.email === 'string' ? route.query.email : '')
const code = ref('')
const error = ref('')
const notice = ref('')
const busy = ref(false)
const purpose = computed(() => route.query.purpose === 'password_reset' ? 'password_reset' : 'signup')
const title = computed(() => purpose.value === 'signup' ? 'Verify your email' : 'Verify your reset code')

async function submit() {
  error.value = ''; notice.value = ''; busy.value = true
  try {
    await auth.verifyOtp(email.value.trim(), code.value.trim(), purpose.value)
    if (purpose.value === 'signup') {
      const fallback = route.query.role === 'owner' ? '/list-property' : '/properties'
      await router.push(safeRedirect(route.query.redirect, fallback))
    } else {
      await router.push({ name: 'reset-password', query: { email: email.value.trim(), step: 'set-password' } })
    }
  } catch (e) { error.value = parseApiError(e).message }
  finally { busy.value = false }
}
async function resend() {
  error.value = ''; notice.value = ''; busy.value = true
  try { await auth.resendOtp(email.value.trim(), purpose.value); notice.value = 'If this account is eligible, a new code has been sent.' }
  catch (e) { error.value = parseApiError(e).message }
  finally { busy.value = false }
}
</script>

<template>
  <section class="page-wrap py-8 sm:py-14">
    <div class="mx-auto max-w-md rounded-3xl bg-white p-6 sm:p-8">
      <h1 class="text-3xl font-extrabold">{{ title }}</h1>
      <p class="mt-2 text-muted">Enter the 6-digit code sent to your email. It expires in 10 minutes.</p>
      <form class="mt-6 space-y-4" @submit.prevent="submit">
        <div><label class="label" for="otp-email">Email</label><input id="otp-email" v-model="email" class="input" type="email" autocomplete="email" required /></div>
        <div><label class="label" for="otp-code">6-digit code</label><input id="otp-code" v-model="code" class="input" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" minlength="6" required /></div>
        <p v-if="error" class="rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ error }}</p>
        <p v-if="notice" class="rounded-xl border border-line p-3" role="status">{{ notice }}</p>
        <button class="btn btn-primary w-full" type="submit" :disabled="busy">{{ busy ? 'Verifying...' : 'Verify code' }}</button>
      </form>
      <button type="button" class="mt-4 w-full text-center font-semibold text-brand hover:underline" :disabled="busy || !email" @click="resend">Resend code</button>
    </div>
  </section>
</template>
