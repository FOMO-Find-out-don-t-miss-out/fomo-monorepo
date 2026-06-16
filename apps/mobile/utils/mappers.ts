import type { ApiEvent, UiEvent, UiEventCategory } from '../types/ui';

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
    return new Date(iso).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return '';
  }
}

/**
 * Convert EventDiscoveryResponse to the mobile UI event shape.
 *
 * Limitations (FOMO-167): the discovery endpoint does not yet expose
 * category or hype_score, so both default here until the backend schema
 * is updated.
 */
export function apiEventToUiEvent(event: ApiEvent): UiEvent {
  return {
    id: event.id,
    title: event.title,
    category: 'Music' as UiEventCategory,
    hypeScore: undefined,
    hypeLevel: 'medium',
    venue: event.locationName ?? 'TBA',
    date: event.startTime ? formatDate(event.startTime) : 'TBA',
    time: event.startTime ? formatTime(event.startTime) : '',
  };
}
