<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useForm } from 'vee-validate'
import { z } from 'zod'
import { parseApiError } from '@/lib/api'
import { toFormSchema } from '@/lib/validate'
import { safeRedirect } from '@/router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const submitError = ref('')

const schema = z.object({
  email: z.string().trim().email('Enter a valid email address.'),
  password: z.string().min(1, 'Enter your password.'),
})

const { defineField, errors, handleSubmit, isSubmitting } = useForm({
  validationSchema: toFormSchema(schema),
  initialValues: { email: '', password: '' },
})
const lazy = (state: { errors: string[] }) => ({ validateOnModelUpdate: state.errors.length > 0 })
const [email, emailAttrs] = defineField('email', lazy)
const [password, passwordAttrs] = defineField('password', lazy)

const onSubmit = handleSubmit(async (values) => {
  submitError.value = ''
  try {
    await auth.login(values.email, values.password)
    // Staff land on their dashboard after a normal login; everyone else on the site.
    await router.push(safeRedirect(route.query.redirect, auth.isStaff ? '/admin' : '/'))
  } catch (e) {
    const parsed = parseApiError(e)
    submitError.value = parsed.message.toLowerCase().includes('no active account')
      ? 'Email or password is incorrect.'
      : parsed.message
  }
})
</script>

<template>
  <section class="page-wrap py-8 sm:py-14" aria-labelledby="login-title">
    <div class="mx-auto max-w-md rounded-3xl bg-white p-6 sm:p-8">
      <h1 id="login-title" class="text-3xl font-extrabold">Login</h1>
      <p class="mt-1 text-muted">Welcome back. Sign in to save properties or manage your listings.</p>

      <form class="mt-6 space-y-4" novalidate @submit.prevent="onSubmit">
        <div>
          <label for="login-email" class="label">Email</label>
          <input id="login-email" v-model="email" v-bind="emailAttrs" type="email" inputmode="email" autocomplete="email" class="input" :aria-invalid="Boolean(errors.email)" :aria-describedby="errors.email ? 'login-email-error' : undefined" />
          <p v-if="errors.email" id="login-email-error" class="field-error">{{ errors.email }}</p>
        </div>
        <div>
          <label for="login-password" class="label">Password</label>
          <input id="login-password" v-model="password" v-bind="passwordAttrs" type="password" autocomplete="current-password" class="input" :aria-invalid="Boolean(errors.password)" :aria-describedby="errors.password ? 'login-password-error' : undefined" />
          <p v-if="errors.password" id="login-password-error" class="field-error">{{ errors.password }}</p>
        </div>

        <p v-if="submitError" class="rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ submitError }}</p>

        <button type="submit" class="btn btn-primary w-full" :disabled="isSubmitting">
          {{ isSubmitting ? 'Signing in...' : 'Login' }}
        </button>
        <RouterLink :to="{ name: 'reset-password', query: route.query }" class="items-center font-semibold text-brand hover:underline">reset password</RouterLink>
      </form>

      <p class="mt-6 text-center text-muted">
        New to Axora?
        <RouterLink :to="{ name: 'signup', query: route.query }" class="inline-flex min-h-11 items-center font-semibold text-brand hover:underline">Create an account</RouterLink>
      </p>
    </div>
  </section>
</template>
