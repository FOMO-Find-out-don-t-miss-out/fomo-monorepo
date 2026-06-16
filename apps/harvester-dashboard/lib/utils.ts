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
