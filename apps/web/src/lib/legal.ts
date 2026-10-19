import { SITE } from '@/lib/site'

export interface LegalSection {
  heading: string
  body: string[]
}

export interface LegalPage {
  slug: string
  title: string
  intro: string
  sections: LegalSection[]
}

const contact = `Questions? Email ${SITE.email} or call ${SITE.phone}.`

export const LEGAL_PAGES: LegalPage[] = [
  {
    slug: 'terms',
    title: 'Terms',
    intro: 'These terms apply when you browse listings, request an inspection, or list a property on Axora Finds.',
    sections: [
      {
        heading: 'Listings',
        body: [
          'Owners submit listings and our team reviews them. A listing appears on the site only after staff publish it.',
          'Availability and price can change. Confirm details at the inspection before you commit to anything.',
        ],
      },
      {
        heading: 'Accounts',
        body: [
          'Accounts are either seeker or owner accounts. Keep your password private and give accurate details.',
          'We may remove listings or close accounts that are misleading or misuse the service.',
        ],
      },
      { heading: 'Contact', body: [contact] },
    ],
  },
  {
    slug: 'privacy',
    title: 'Privacy',
    intro: 'What we collect, and why.',
    sections: [
      {
        heading: 'What we collect',
        body: [
          'Account details (name, email, phone), inspection requests (contact details, preferred date, note), listing details and photos, contact messages, and newsletter email addresses.',
          'We do not take card numbers on this site.',
        ],
      },
      {
        heading: 'How we use it',
        body: [
          'To follow up on inspection requests, verify payments, review listings, answer messages, and send the newsletter to people who signed up for it.',
        ],
      },
      {
        heading: 'Your choices',
        body: [`To correct or delete your details, or to leave the newsletter, contact us. ${contact}`],
      },
    ],
  },
  {
    slug: 'inspection-refund-policy',
    title: 'Inspection and Refund Policy',
    intro: 'How inspection requests, inspection fees and refunds work.',
    sections: [
      {
        heading: 'A request is not a confirmation',
        body: [
          'When you request an inspection, its status is pending. Our team confirms the visit only after the request, and any inspection fee, has been verified.',
        ],
      },
      {
        heading: 'Paying an inspection fee',
        body: [
          'If a listing has an inspection fee, the amount is shown before you submit. You can pay by bank transfer or choose to pay in person.',
          'For bank transfer, the official account appears only after your request is submitted. Pay only to that account and use your reference.',
          'Choosing to pay in person is a request. It is stored as unpaid until our team verifies payment.',
        ],
      },
      {
        heading: 'Refunds',
        body: [
          `If an inspection is rejected or cannot go ahead, contact us with your reference and staff will review the payment. ${contact}`,
        ],
      },
    ],
  },
  {
    slug: 'rental-agreement',
    title: 'Rental Agreement',
    intro: 'What to know before you sign a tenancy.',
    sections: [
      {
        heading: 'Between landlord and tenant',
        body: [
          'A tenancy agreement is made between the property owner and the tenant. Axora Finds helps you find and inspect a home; it does not collect rent on this site.',
          'An inspection fee is not rent and does not reserve a property.',
        ],
      },
      {
        heading: 'Before you sign',
        body: [
          'Read the whole agreement, check the rent, the payment period and any other charges, and keep a signed copy.',
        ],
      },
      { heading: 'Contact', body: [contact] },
    ],
  },
]

export function findLegalPage(slug: string): LegalPage | undefined {
  return LEGAL_PAGES.find((p) => p.slug === slug)
}
