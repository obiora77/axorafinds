<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useForm } from 'vee-validate'
import { z } from 'zod'
import { parseApiError } from '@/lib/api'
import { toFormSchema } from '@/lib/validate'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const submitError = ref('')
const notice = ref('')
const step = ref(route.query.step === 'set-password' ? 'set-password' : 'request')
const emailSchema = z.object({ email: z.string().trim().email('Enter your registered email') })
const { defineField, errors, handleSubmit, isSubmitting, setErrors } = useForm({
  validationSchema: toFormSchema(emailSchema),
  initialValues: { email: typeof route.query.email === 'string' ? route.query.email : '' },
})
const lazy = (state: { errors: string[] }) => ({ validateOnModelUpdate: state.errors.length > 0 })
const [email, emailAttrs] = defineField('email', lazy)
const code = ref('')
const password = ref('')
const confirmPassword = ref('')
const title = computed(() => step.value === 'request' ? 'Reset Password' : 'Choose a new password')

const requestCode = handleSubmit(async (values) => {
  submitError.value = ''; notice.value = ''
  try {
    await auth.requestPasswordReset(values.email.trim())
    notice.value = 'If an active account exists for that email, a reset code has been sent.'
    await router.replace({ query: { email: values.email.trim(), step: 'set-password' } })
    step.value = 'set-password'
  } catch (e) {
    const parsed = parseApiError(e); submitError.value = parsed.message
    if (Object.keys(parsed.fields).length) setErrors(parsed.fields)
  }
})

async function setNewPassword() {
  submitError.value = ''; notice.value = ''
  if (!/^\d{6}$/.test(code.value)) { submitError.value = 'Enter the 6-digit code from your email.'; return }
  if (password.value.length < 8) { submitError.value = 'Use a password with at least 8 characters.'; return }
  if (password.value !== confirmPassword.value) { submitError.value = 'The passwords do not match.'; return }
  try {
    await auth.confirmPasswordReset(email.value.trim(), code.value, password.value)
    notice.value = 'Password reset successfully. You can now log in.'
    setTimeout(() => router.push({ name: 'login' }), 1200)
  } catch (e) { submitError.value = parseApiError(e).message }
}
</script>

<template>
  <section class="page-wrap py-8 sm:py-14" aria-labelledby="reset-title">
    <div class="mx-auto max-w-md rounded-3xl bg-white p-6 sm:p-8">
      <h1 id="reset-title" class="text-3xl font-extrabold">{{ title }}</h1>
      <p class="mt-1 text-muted">{{ step === 'request' ? 'We will email you a one-time code to reset your password.' : 'Enter the code from your email and choose a new password.' }}</p>
      <form v-if="step === 'request'" class="mt-6 space-y-4" novalidate @submit.prevent="requestCode">
        <div><label for="reset-email" class="label">Email</label><input id="reset-email" v-model="email" v-bind="emailAttrs" type="email" autocomplete="email" class="input" :aria-invalid="Boolean(errors.email)" required /><p v-if="errors.email" class="field-error">{{ errors.email }}</p></div>
        <p v-if="submitError" class="rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ submitError }}</p>
        <p v-if="notice" class="rounded-xl border border-line p-3" role="status">{{ notice }}</p>
        <button type="submit" class="btn btn-primary w-full" :disabled="isSubmitting">{{ isSubmitting ? 'Sending code...' : 'Send reset code' }}</button>
      </form>
      <form v-else class="mt-6 space-y-4" @submit.prevent="setNewPassword">
        <div><label for="reset-email-confirm" class="label">Email</label><input id="reset-email-confirm" v-model="email" type="email" class="input" autocomplete="email" required /></div>
        <div><label for="reset-code" class="label">6-digit code</label><input id="reset-code" v-model="code" class="input" inputmode="numeric" autocomplete="one-time-code" maxlength="6" required /></div>
        <div><label for="reset-password" class="label">New password</label><input id="reset-password" v-model="password" type="password" class="input" autocomplete="new-password" minlength="8" required /></div>
        <div><label for="reset-confirm-password" class="label">Confirm new password</label><input id="reset-confirm-password" v-model="confirmPassword" type="password" class="input" autocomplete="new-password" minlength="8" required /></div>
        <p v-if="submitError" class="rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ submitError }}</p>
        <p v-if="notice" class="rounded-xl border border-line p-3" role="status">{{ notice }}</p>
        <button type="submit" class="btn btn-primary w-full">Reset password</button>
        <button type="button" class="w-full text-center font-semibold text-brand hover:underline" @click="step = 'request'">Send another code</button>
      </form>
    </div>
  </section>
</template>
