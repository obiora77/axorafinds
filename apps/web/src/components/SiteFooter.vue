<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { Mail, MapPin, Phone } from 'lucide-vue-next'
import NewsletterForm from '@/components/NewsletterForm.vue'
import { LEGAL_LINKS, QUICK_LINKS, SITE } from '@/lib/site'
</script>

<template>
  <footer class="on-dark bg-footer text-white" style="padding-bottom: env(safe-area-inset-bottom)">
    <div class="page-wrap py-12">
      <div class="grid gap-10 md:grid-cols-2 lg:grid-cols-4">
        <div>
          <img src="/logo.svg" alt="Axora Finds" width="138" height="32" class="h-8 w-auto" />
          <h2 class="mt-5 text-xl font-bold leading-snug">List Your Properties, Reach More People Faster.</h2>
          <RouterLink to="/list-property" class="btn btn-primary mt-5">List your property</RouterLink>
        </div>

        <nav aria-label="Quick links">
          <h2 class="text-base font-bold">Quick links</h2>
          <ul class="mt-3">
            <li v-for="link in QUICK_LINKS" :key="link.to">
              <RouterLink :to="link.to" class="inline-flex min-h-11 items-center text-white hover:underline">
                {{ link.label }}
              </RouterLink>
            </li>
          </ul>
        </nav>

        <div>
          <h2 class="text-base font-bold">Contact</h2>
          <ul class="mt-3 space-y-1">
            <li>
              <a :href="`mailto:${SITE.email}`" class="inline-flex min-h-11 items-center gap-2.5 hover:underline">
                <Mail class="size-5 shrink-0" aria-hidden="true" />
                {{ SITE.email }}
              </a>
            </li>
            <li>
              <a :href="`tel:${SITE.phone}`" class="inline-flex min-h-11 items-center gap-2.5 hover:underline">
                <Phone class="size-5 shrink-0" aria-hidden="true" />
                {{ SITE.phone }}
              </a>
            </li>
            <li class="inline-flex min-h-11 items-center gap-2.5">
              <MapPin class="size-5 shrink-0" aria-hidden="true" />
              {{ SITE.location }}
            </li>
          </ul>
        </div>

        <div>
          <h2 class="text-base font-bold">Newsletter</h2>
          <p class="mb-3 mt-3 text-sm text-white">New verified listings, straight to your inbox.</p>
          <NewsletterForm />
        </div>
      </div>

      <div
        class="mt-10 flex flex-col gap-3 border-t border-white/20 pt-6 md:flex-row md:items-center md:justify-between"
      >
        <p class="text-sm text-white">{{ SITE.copyright }}</p>
        <ul class="flex flex-wrap gap-x-5">
          <li v-for="link in LEGAL_LINKS" :key="link.to">
            <RouterLink :to="link.to" class="inline-flex min-h-11 items-center text-sm text-white hover:underline">
              {{ link.label }}
            </RouterLink>
          </li>
        </ul>
      </div>
    </div>
  </footer>
</template>
