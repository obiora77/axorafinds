<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { apiFetch, parseApiError } from '@/lib/api'
import type { StaffSiteSettings } from '@/types'

const form = reactive({
  bank_name: '',
  account_name: '',
  account_number: '',
  transfer_note: '',
  is_live: false,
})

const hasAccount = ref(false)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const notice = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const settings = await apiFetch<StaffSiteSettings>('/staff/settings')
    form.bank_name = settings.bank_name
    form.account_name = settings.account_name
    form.account_number = settings.account_number
    form.transfer_note = settings.transfer_note
    form.is_live = settings.is_live
    hasAccount.value = settings.has_account
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    loading.value = false
  }
}

async function save(): Promise<void> {
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const settings = await apiFetch<StaffSiteSettings>('/staff/settings', {
      method: 'PUT',
      body: { ...form },
    })
    hasAccount.value = settings.has_account
    notice.value = settings.is_live
      ? 'Bank details saved and marked live. The payment account can now be shown on the site.'
      : 'Bank details saved. They stay hidden until “Is live” is ticked.'
  } catch (e) {
    error.value = parseApiError(e).message
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="max-w-2xl">
    <h2 class="font-display text-xl font-bold text-ink">Payment account</h2>
    <p class="mt-1 text-sm text-muted">
      This is the only place the official account lives. It is never hardcoded in the site and is
      only revealed to a visitor who just created a bank-transfer inspection request.
    </p>

    <p v-if="error" class="mt-4 rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ error }}</p>
    <p v-if="notice" class="mt-4 rounded-xl border border-line bg-white p-3 font-medium text-ink" role="status">{{ notice }}</p>

    <p v-if="loading" class="mt-4 text-muted" role="status">Loading settings…</p>

    <form v-else class="mt-5 space-y-4" @submit.prevent="save">
      <div>
        <label for="bank-name" class="label">Bank name</label>
        <input id="bank-name" v-model="form.bank_name" type="text" maxlength="80" class="input" autocomplete="organization" />
      </div>
      <div>
        <label for="account-name" class="label">Account name</label>
        <input id="account-name" v-model="form.account_name" type="text" maxlength="120" class="input" />
      </div>
      <div>
        <label for="account-number" class="label">Account number</label>
        <input id="account-number" v-model="form.account_number" type="text" inputmode="numeric" maxlength="20" class="input" />
      </div>
      <div>
        <label for="transfer-note" class="label">Transfer note</label>
        <textarea
          id="transfer-note"
          v-model="form.transfer_note"
          rows="3"
          class="input"
          placeholder="For example: Use your inspection reference as the narration."
        />
        <p class="hint">Shown under the bank details on the listing page.</p>
      </div>
      <label class="flex items-start gap-3 rounded-2xl border border-line p-4">
        <input v-model="form.is_live" type="checkbox" class="mt-1 size-5 shrink-0" />
        <span>
          <span class="block font-semibold text-ink">Is live</span>
          <span class="block text-sm text-muted">
            Tick this only when the real bank details above are correct. While unticked, the account is
            hidden in production (and shown only in debug mode with demo data).
          </span>
        </span>
      </label>

      <div class="flex flex-wrap items-center gap-3">
        <button type="submit" class="btn btn-primary" :disabled="saving">
          {{ saving ? 'Saving…' : 'Save settings' }}
        </button>
        <span class="text-sm" :class="hasAccount ? 'text-green-700' : 'text-muted'">
          {{ hasAccount ? 'Account details are complete.' : 'Bank name, account name and number are required.' }}
        </span>
      </div>

      <p class="rounded-2xl bg-white p-4 text-sm text-muted">
        The same row appears in <strong>Django admin → Pages → Site settings</strong>. Changes here are
        visible there immediately.
      </p>
    </form>
  </div>
</template>
