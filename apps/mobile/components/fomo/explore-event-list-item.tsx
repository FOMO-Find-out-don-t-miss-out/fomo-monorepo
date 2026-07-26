import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { Colors, Typography } from '../../theme';
import {
  perfClaimImageSample,
  perfCountRender,
  perfLog,
  perfMark,
  perfSince,
} from '../../utils/performance-debug';
import { backendCategoryLabel } from '../../utils/explore-filters';

import type { ExploreEvent } from '../../hooks/use-explore-search';

// ─── Props ────────────────────────────────────────────────────────────────────

interface ExploreEventListItemProps {
  event: ExploreEvent;
  onPress: (id: string) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const FALLBACK_FONT_FAMILY = Typography.font.bold;
const FALLBACK_FONT_SIZE = 10;

function categoryTokens(rawCategory: string) {
  const cat = Colors.exploreCategory[rawCategory];
  if (cat) return cat;
  return Colors.exploreCategory.Other;
}

// ─── Component ────────────────────────────────────────────────────────────────

function ExploreEventListItemBase({ event, onPress }: ExploreEventListItemProps) {
  perfCountRender('ExploreEventListItem', 25);

  // Image-load timing for a capped sample (matches EventCard's pattern).
  const imageSampleRef = useRef<number | null | undefined>(undefined);
  if (imageSampleRef.current === undefined) {
    imageSampleRef.current = event.imageUri ? perfClaimImageSample() : null;
  }
  const imageMarkRef = useRef(0);

  const [imageFailed, setImageFailed] = useState(false);

  // Reset image failure when the imageUri changes (handles FlatList recycling).
  useEffect(() => {
    setImageFailed(false);
  }, [event.imageUri]);

  const showImage = event.imageUri && !imageFailed;

  const handleImageError = useCallback(() => {
    // Do not log a successful load — the image failed.
    imageSampleRef.current = null;
    setImageFailed(true);
  }, []);

  const cat = categoryTokens(event.rawCategory);
  const displayCategory = backendCategoryLabel(event.rawCategory);

  const hasDate = event.date && event.date !== 'TBA';
  const hasTime = Boolean(event.time);
  const dateTimeParts: string[] = [];
  if (hasDate) dateTimeParts.push(event.date);
  if (hasTime) dateTimeParts.push(event.time);

  const hasVenue = event.venue && event.venue !== 'TBA';

  // Accessibility label — filtered, no empty/TBA segments.
  const a11yParts: string[] = [event.title];
  a11yParts.push(displayCategory);
  if (hasDate) a11yParts.push(event.date);
  if (hasTime) a11yParts.push(`at ${event.time}`);
  if (hasVenue) a11yParts.push(event.venue);

  return (
    <TouchableOpacity
      onPress={() => onPress(event.id)}
      style={styles.cell}
      activeOpacity={0.65}
      accessibilityRole="button"
      accessibilityHint="Opens event details"
      accessibilityLabel={a11yParts.join(', ')}
    >
      {/* ── Thumbnail (always present) ─────────────────────────────────── */}
      <View style={[styles.thumbnail, { backgroundColor: cat.bg, borderColor: cat.border }]}>
        {/* FOMO fallback always underneath */}
        <Text style={[styles.fallbackText, { color: cat.text }]}>FOMO</Text>

        {/* Real image on top when available and not failed */}
        {showImage && (
          <Image
            source={{ uri: event.imageUri! }}
            style={styles.image}
            resizeMode="cover"
            {...(imageSampleRef.current != null
              ? {
                  onLoadStart: () => {
                    imageMarkRef.current = perfMark();
                  },
                  onLoad: () => {
                    perfLog('image', {
                      sample: imageSampleRef.current,
                      duration_ms: perfSince(imageMarkRef.current),
                    });
                  },
                }
              : {})}
            onError={handleImageError}
          />
        )}
      </View>

      {/* ── Content column ─────────────────────────────────────────────── */}
      <View style={styles.content}>
        {/* Title */}
        <Text style={styles.title} numberOfLines={2} ellipsizeMode="tail">
          {event.title}
        </Text>

        {/* Date / time */}
        {dateTimeParts.length > 0 && (
          <Text style={styles.dateTime} numberOfLines={1} ellipsizeMode="tail">
            {dateTimeParts.join(' · ')}
          </Text>
        )}

        {/* Venue + category footer */}
        {(hasVenue || displayCategory) ? (
          <View style={styles.footer}>
            {hasVenue && (
              <Text style={styles.venue} numberOfLines={1} ellipsizeMode="tail">
                {event.venue}
              </Text>
            )}
            <Text
              style={[styles.category, { color: cat.text }]}
              numberOfLines={1}
            >
              {displayCategory}
            </Text>
          </View>
        ) : null}
      </View>
    </TouchableOpacity>
  );
}

export const ExploreEventListItem = React.memo(ExploreEventListItemBase);

// ─── Styles ───────────────────────────────────────────────────────────────────

const THUMBNAIL_SIZE = 56;
const CELL_RADIUS = 12;
const THUMBNAIL_RADIUS = 10;
const CELL_GAP = 10;
const CELL_MARGIN_BOTTOM = 8;

const styles = StyleSheet.create({
  cell: {
    alignSelf: 'stretch',
    marginHorizontal: 16,
    marginBottom: CELL_MARGIN_BOTTOM,
    backgroundColor: Colors.surfaceCard,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.borderSubtle,
    borderRadius: CELL_RADIUS,
    overflow: 'hidden',
    paddingHorizontal: 10,
    paddingVertical: 10,
    flexDirection: 'row',
    alignItems: 'center',
  },

  // ── Thumbnail ───────────────────────────────────────────────────────
  thumbnail: {
    width: THUMBNAIL_SIZE,
    height: THUMBNAIL_SIZE,
    borderRadius: THUMBNAIL_RADIUS,
    borderWidth: StyleSheet.hairlineWidth,
    flexShrink: 0,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  fallbackText: {
    fontFamily: FALLBACK_FONT_FAMILY,
    fontSize: FALLBACK_FONT_SIZE,
    letterSpacing: 0.5,
  },
  image: {
    ...StyleSheet.absoluteFillObject,
  },

  // ── Content column ──────────────────────────────────────────────────
  content: {
    flex: 1,
    minWidth: 0,
    flexShrink: 1,
    alignSelf: 'stretch',
    marginLeft: CELL_GAP,
    justifyContent: 'center',
  },

  title: {
    fontFamily: Typography.font.semiBold,
    fontSize: Typography.size.md,
    lineHeight: 18,
    color: Colors.textPrimary,
    includeFontPadding: false,
  },

  dateTime: {
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.sm,
    color: Colors.textMuted,
    includeFontPadding: false,
    marginTop: 3,
  },

  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 3,
    minWidth: 0,
  },
  venue: {
    flex: 1,
    minWidth: 0,
    fontFamily: Typography.font.regular,
    fontSize: Typography.size.sm + 1, // 12px — between sm(11) and base(13)
    color: Colors.textSecondary,
    includeFontPadding: false,
  },
  category: {
    flexShrink: 0,
    marginLeft: 8,
    fontFamily: Typography.font.medium,
    fontSize: Typography.size.xs + 1, // 10px
  },
});
