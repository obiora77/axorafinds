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
  name: z.string().trim().min(2, 'Enter your full name.'),
  email: z.string().trim().email('Enter a valid email address.'),
  phone: z.string().trim().regex(/^(\+?[0-9 ()-]{10,20})?$/, 'Enter a valid phone number or leave it empty.'),
  password: z.string().min(8, 'Use at least 8 characters.'),
  role: z.enum(['seeker', 'owner']),
})

const { defineField, errors, handleSubmit, isSubmitting, setErrors } = useForm({
  validationSchema: toFormSchema(schema),
  initialValues: {
    name: '',
    email: '',
    phone: '',
    password: '',
    role: route.query.role === 'owner' ? ('owner' as const) : ('seeker' as const),
  },
})
const lazy = (state: { errors: string[] }) => ({ validateOnModelUpdate: state.errors.length > 0 })
const [name, nameAttrs] = defineField('name', lazy)
const [email, emailAttrs] = defineField('email', lazy)
const [phone, phoneAttrs] = defineField('phone', lazy)
const [password, passwordAttrs] = defineField('password', lazy)
const [role] = defineField('role')

const onSubmit = handleSubmit(async (values) => {
  submitError.value = ''
  try {
    const result = await auth.register({
      name: values.name,
      email: values.email,
      password: values.password,
      role: values.role,
      ...(values.phone ? { phone: values.phone } : {}),
    })
    await router.push({ name: 'otp', query: { email: result.email, purpose: 'signup', redirect: route.query.redirect, role: values.role } })
  } catch (e) {
    const parsed = parseApiError(e)
    submitError.value = parsed.message
    if (Object.keys(parsed.fields).length) setErrors(parsed.fields)
  }
})
</script>

<template>
  <section class="page-wrap py-8 sm:py-14" aria-labelledby="signup-title">
    <div class="mx-auto max-w-md rounded-3xl bg-white p-6 sm:p-8">
      <h1 id="signup-title" class="text-3xl font-extrabold">Sign Up</h1>
      <p class="mt-1 text-muted">Create an account to save properties or list your own.</p>

      <form class="mt-6 space-y-4" novalidate @submit.prevent="onSubmit">
        <fieldset>
          <legend class="label">I want to</legend>
          <div class="grid gap-2 sm:grid-cols-2">
            <label class="flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border border-line p-3 has-[:checked]:border-ink">
              <input v-model="role" type="radio" value="seeker" name="role" class="size-5 accent-brand" />
              <span class="font-semibold">Find a property</span>
            </label>
            <label class="flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border border-line p-3 has-[:checked]:border-ink">
              <input v-model="role" type="radio" value="owner" name="role" class="size-5 accent-brand" />
              <span class="font-semibold">List a property</span>
            </label>
          </div>
        </fieldset>

        <div>
          <label for="signup-name" class="label">Full name</label>
          <input id="signup-name" v-model="name" v-bind="nameAttrs" type="text" autocomplete="name" class="input" :aria-invalid="Boolean(errors.name)" :aria-describedby="errors.name ? 'signup-name-error' : undefined" />
          <p v-if="errors.name" id="signup-name-error" class="field-error">{{ errors.name }}</p>
        </div>
        <div>
          <label for="signup-email" class="label">Email</label>
          <input id="signup-email" v-model="email" v-bind="emailAttrs" type="email" inputmode="email" autocomplete="email" class="input" :aria-invalid="Boolean(errors.email)" :aria-describedby="errors.email ? 'signup-email-error' : undefined" />
          <p v-if="errors.email" id="signup-email-error" class="field-error">{{ errors.email }}</p>
        </div>
        <div>
          <label for="signup-phone" class="label">Phone <span class="font-normal text-muted">(optional)</span></label>
          <input id="signup-phone" v-model="phone" v-bind="phoneAttrs" type="tel" inputmode="tel" autocomplete="tel" class="input" :aria-invalid="Boolean(errors.phone)" :aria-describedby="errors.phone ? 'signup-phone-error' : undefined" />
          <p v-if="errors.phone" id="signup-phone-error" class="field-error">{{ errors.phone }}</p>
        </div>
        <div>
          <label for="signup-password" class="label">Password</label>
          <input id="signup-password" v-model="password" v-bind="passwordAttrs" type="password" autocomplete="new-password" class="input" :aria-invalid="Boolean(errors.password)" aria-describedby="signup-password-hint" />
          <p v-if="errors.password" class="field-error">{{ errors.password }}</p>
          <p id="signup-password-hint" class="hint">At least 8 characters.</p>
        </div>

        <p v-if="submitError" class="rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ submitError }}</p>

        <button type="submit" class="btn btn-primary w-full" :disabled="isSubmitting">
          {{ isSubmitting ? 'Creating account...' : 'Create account' }}
        </button>
      </form>

      <p class="mt-6 text-center text-muted">
        Already have an account?
        <RouterLink :to="{ name: 'login', query: route.query }" class="inline-flex min-h-11 items-center font-semibold text-brand hover:underline">Login</RouterLink>
      </p>
    </div>
  </section>
</template>
