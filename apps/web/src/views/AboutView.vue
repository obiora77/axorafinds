<script setup lang="ts">
import { LayoutList, Search, Wallet } from 'lucide-vue-next'
import { SITE } from '@/lib/site'
import { heroIn, reveal } from '@/plugins/motion'

const pillars = [
  {
    icon: Search,
    title: 'Easier',
    text: 'Browse verified homes and land in one place and request an inspection in a few taps.',
  },
  {
    icon: Wallet,
    title: 'Cheaper',
    text: 'We exist to cut the high agent fees that come with house hunting.',
  },
  {
    icon: LayoutList,
    title: 'More organised',
    text: 'Listings are reviewed before they go live, and every request is tracked from pending to confirmed.',
  },
] as const

const steps = [
  { title: 'Browse', text: 'Filter by state, city, type, price and bedrooms.' },
  { title: 'Request an inspection', text: 'Send your contact details and a preferred date. Pay the inspection fee, if there is one, by bank transfer or in person.' },
  { title: 'We verify, then confirm', text: 'Our team checks your request and any payment first. Only then is the visit confirmed.' },
] as const
</script>

<template>
  <div>
    <section class="on-red text-white" aria-labelledby="about-title">
      <div v-motion v-bind="heroIn()" class="page-wrap py-10 lg:py-16">
        <h1 id="about-title" class="text-4xl font-extrabold leading-tight sm:text-5xl lg:text-6xl">{{ SITE.tagline }}</h1>
        <p class="mt-4 max-w-xl text-xl">{{ SITE.promise }}</p>
      </div>
    </section>

    <section class="panel">
      <div class="page-wrap py-10 lg:py-14">
        <div v-motion v-bind="reveal()" class="max-w-prose">
          <h2 class="text-2xl font-extrabold sm:text-3xl">What Axora Finds is</h2>
          <p class="mt-3 text-lg leading-relaxed">
            Axora Finds is a property-finding service for rentals in Nigeria. People browse verified homes and land, request an
            inspection, and owners list their properties. The goal is a search that is easier, cheaper and more organised than
            the usual round of agents.
          </p>
        </div>

        <ul class="mt-10 grid gap-5 md:grid-cols-3">
          <li v-for="(pillar, index) in pillars" :key="pillar.title" v-motion v-bind="reveal(index * 60)" class="rounded-2xl border border-line p-5">
            <component :is="pillar.icon" class="size-8 text-brand" aria-hidden="true" />
            <h3 class="mt-3 text-xl font-bold">{{ pillar.title }}</h3>
            <p class="mt-1 text-muted">{{ pillar.text }}</p>
          </li>
        </ul>

        <div v-motion v-bind="reveal()" class="mt-12 max-w-prose">
          <h2 class="text-2xl font-extrabold sm:text-3xl">How it works</h2>
          <ol class="mt-4 space-y-4">
            <li v-for="(step, index) in steps" :key="step.title" class="flex gap-4">
              <span class="grid size-9 shrink-0 place-items-center rounded-full bg-brand font-bold text-white" aria-hidden="true">{{ index + 1 }}</span>
              <div>
                <h3 class="text-lg font-bold">{{ step.title }}</h3>
                <p class="text-muted">{{ step.text }}</p>
              </div>
            </li>
          </ol>
          <div class="mt-8 flex flex-col gap-3 sm:flex-row">
            <RouterLink to="/properties" class="btn btn-primary">Browse properties</RouterLink>
            <RouterLink to="/list-property" class="btn btn-outline">List your property</RouterLink>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
