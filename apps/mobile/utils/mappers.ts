import type { ApiEvent, ApiEventCategory, UiEvent, UiEventCategory } from '../types/ui';
import { apiCategoryToUi } from '../types/ui';

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
  } catch {
    return '';
  }
}

function toHypeLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 70) return 'high';
  if (score >= 40) return 'medium';
  return 'low';
}

const KNOWN_CATEGORIES = new Set<string>([
  'Music', 'Art', 'Tech', 'Food', 'Nightlife', 'Sports', 'Business', 'Community', 'Other',
]);

function toUiCategory(raw: string): UiEventCategory {
  const key = KNOWN_CATEGORIES.has(raw) ? (raw as ApiEventCategory) : 'Other';
  return apiCategoryToUi[key];
}

export function apiEventToUiEvent(event: ApiEvent): UiEvent {
  const hypeScore = event.hypeScore ?? 0;
  return {
    id: event.id,
    title: event.title,
    category: toUiCategory(event.category ?? 'Other'),
    hypeScore,
    hypeLevel: toHypeLevel(hypeScore),
    venue: event.locationName ?? 'TBA',
    date: event.startTime ? formatDate(event.startTime) : 'TBA',
    time: event.startTime ? formatTime(event.startTime) : '',
    imageUri: event.photoUrl ?? null,
    ticketUrl: event.ticketUrl ?? null,
    sourceUrl: event.sourceUrl ?? null,
    lat: event.lat,
    lng: event.lng,
    startTime: event.startTime ?? undefined,
  };
}
