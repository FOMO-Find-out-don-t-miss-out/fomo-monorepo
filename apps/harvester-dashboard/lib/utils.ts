import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * The backend's source of truth for place verification is verification_status
 * (unverified | system_matched | manually_verified) — there is no separate
 * boolean field. Derive the boolean here instead of trusting a phantom
 * is_manually_verified field that PlaceResponse never actually sends.
 */
export function isPlaceVerified(place: { verification_status?: string }): boolean {
  return place.verification_status === 'manually_verified'
}

/** FOMO-16: human-readable label for a pending event's dedupe_status, with an unknown-value fallback. */
export function dedupeStatusLabel(status: string): string {
  switch (status) {
    case 'not_checked':
      return 'Not checked'
    case 'duplicate_confirmed':
      return 'Duplicate confirmed'
    case 'possible_match':
      return 'Possible match'
    case 'no_match':
      return 'No match'
    case 'merged':
      return 'Merged'
    default:
      return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }
}
