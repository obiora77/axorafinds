export const SITE = {
  name: 'Axora Finds',
  email: 'axorafinds@gmail.com',
  phone: '07044453444',
  location: 'Nigeria',
  copyright: '\u00a9 2026 AXORA. All rights reserved.',
  tagline: 'Finding homes. Building trust.',
  promise: 'Helping you find a home without the usual high agency fees.',
} as const

export const QUICK_LINKS = [
  { label: 'Home', to: '/' },
  { label: 'Marketplace', to: '/properties' },
  { label: 'For Owners', to: '/list-property' },
  { label: 'About Us', to: '/about' },
  { label: 'Contact Us', to: '/contact' },
] as const

export const LEGAL_LINKS = [
  { label: 'Terms', to: '/legal/terms' },
  { label: 'Privacy', to: '/legal/privacy' },
  { label: 'Inspection and Refund Policy', to: '/legal/inspection-refund-policy' },
  { label: 'Rental Agreement', to: '/legal/rental-agreement' },
] as const

/** Keep in sync with STATES in apps/api/listings/models.py. */
export const NG_STATES = [
  'Abia', 'Adamawa', 'Akwa Ibom', 'Anambra', 'Bauchi', 'Bayelsa', 'Benue', 'Borno',
  'Cross River', 'Delta', 'Ebonyi', 'Edo', 'Ekiti', 'Enugu', 'FCT', 'Gombe', 'Imo',
  'Jigawa', 'Kaduna', 'Kano', 'Katsina', 'Kebbi', 'Kogi', 'Kwara', 'Lagos', 'Nasarawa',
  'Niger', 'Ogun', 'Ondo', 'Osun', 'Oyo', 'Plateau', 'Rivers', 'Sokoto', 'Taraba',
  'Yobe', 'Zamfara',
] as const

/** Keep in sync with PropertyType in apps/api/listings/models.py. */
export const PROPERTY_TYPES = [
  { value: 'room_parlour', label: 'Room and parlour' },
  { value: 'self_contain', label: 'Self-contain' },
  { value: 'flat', label: 'Flat' },
  { value: 'duplex', label: 'Duplex' },
  { value: 'bungalow', label: 'Bungalow' },
  { value: 'land', label: 'Land' },
] as const

export const BEDROOM_OPTIONS = [
  { value: '', label: 'Any bedrooms' },
  { value: '1', label: '1+ bedrooms' },
  { value: '2', label: '2+ bedrooms' },
  { value: '3', label: '3+ bedrooms' },
  { value: '4', label: '4+ bedrooms' },
] as const
