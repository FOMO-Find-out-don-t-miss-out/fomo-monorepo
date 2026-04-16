import { CalendarView } from '../../components/fomo/calendar-view';
import { EventCard, type Event } from '../../components/fomo/event-card';
import { EventDetails } from '../../components/fomo/event-details';
import { FomoMap } from '../../components/fomo/fomo-map';
import { NeonGrid } from '../../components/fomo/neon-grid';
import { SearchBar } from '../../components/fomo/search-bar';
import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Dimensions,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';

// ─── Constants ────────────────────────────────────────────────────────────────

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = 260;
const CARD_GAP   = 16;

// ─── Mock data ────────────────────────────────────────────────────────────────

const EVENTS: Event[] = [
  {
    id: '1',
    title: 'Neon Dreams Festival 2026',
    venue: 'Madison Square Garden',
    date: 'Apr 15, 2026',
    time: '8:00 PM',
    category: 'Festival',
    hypeLevel: 'high',
    price: '$149',
    distance: '2.3 mi',
    attendeesCount: '4.2K',
    hypeScore: 97,
  },
  {
    id: '2',
    title: 'Synthwave Symphony',
    venue: 'Brooklyn Steel',
    date: 'Apr 15, 2026',
    time: '9:00 PM',
    category: 'Music',
    hypeLevel: 'high',
    price: '$75',
    distance: '4.1 mi',
    attendeesCount: '1.8K',
    hypeScore: 91,
  },
  {
    id: '3',
    title: 'Digital Art Exhibition',
    venue: 'MoMA PS1',
    date: 'Apr 15, 2026',
    time: '11:00 AM',
    category: 'Arts',
    hypeLevel: 'medium',
    price: '$25',
    distance: '3.8 mi',
    attendeesCount: '640',
    hypeScore: 74,
  },
  {
    id: '4',
    title: 'Comedy Night Live',
    venue: 'Comedy Cellar',
    date: 'Apr 16, 2026',
    time: '10:00 PM',
    category: 'Comedy',
    hypeLevel: 'medium',
    price: '$35',
    distance: '1.2 mi',
    attendeesCount: '980',
    hypeScore: 81,
  },
  {
    id: '5',
    title: 'Broadway Reimagined',
    venue: 'Lincoln Center',
    date: 'Apr 16, 2026',
    time: '7:30 PM',
    category: 'Theater',
    hypeLevel: 'high',
    price: '$120',
    distance: '5.6 mi',
    attendeesCount: '2.1K',
    hypeScore: 89,
  },
  {
    id: '6',
    title: 'Championship Finals',
    venue: 'Barclays Center',
    date: 'Apr 17, 2026',
    time: '6:00 PM',
    category: 'Sports',
    hypeLevel: 'high',
    price: '$200',
    distance: '6.2 mi',
    attendeesCount: '5.8K',
    hypeScore: 99,
  },
  {
    id: '7',
    title: 'Jazz Under Stars',
    venue: 'Central Park',
    date: 'Apr 17, 2026',
    time: '7:00 PM',
    category: 'Music',
    hypeLevel: 'medium',
    price: '$45',
    distance: '0.8 mi',
    attendeesCount: '760',
    hypeScore: 72,
  },
  {
    id: '8',
    title: 'Stand-Up Showcase',
    venue: 'Gotham Comedy Club',
    date: 'Apr 18, 2026',
    time: '9:30 PM',
    category: 'Comedy',
    hypeLevel: 'medium',
    price: '$30',
    distance: '2.1 mi',
    attendeesCount: '420',
    hypeScore: 68,
  },
  {
    id: '9',
    title: 'Electronic Dreams',
    venue: 'Webster Hall',
    date: 'Apr 18, 2026',
    time: '11:00 PM',
    category: 'Festival',
    hypeLevel: 'high',
    price: '$85',
    distance: '3.2 mi',
    attendeesCount: '3.4K',
    hypeScore: 94,
  },
  {
    id: '10',
    title: 'Modern Dance Collective',
    venue: 'BAM Howard Gilman',
    date: 'Apr 19, 2026',
    time: '8:00 PM',
    category: 'Theater',
    hypeLevel: 'medium',
    price: '$55',
    distance: '4.5 mi',
    attendeesCount: '510',
    hypeScore: 71,
  },
  {
    id: '11',
    title: 'Street Art Tour',
    venue: 'Bushwick Collective',
    date: 'Apr 19, 2026',
    time: '2:00 PM',
    category: 'Arts',
    hypeLevel: 'low',
    price: '$15',
    distance: '5.8 mi',
    attendeesCount: '180',
    hypeScore: 52,
  },
  {
    id: '12',
    title: 'Soccer Championship',
    venue: 'Red Bull Arena',
    date: 'Apr 20, 2026',
    time: '4:00 PM',
    category: 'Sports',
    hypeLevel: 'high',
    price: '$95',
    distance: '8.2 mi',
    attendeesCount: '4.9K',
    hypeScore: 96,
  },
];

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function DiscoveryScreen() {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [isCalendarView, setIsCalendarView] = useState(false);

  const carouselPadding = (SCREEN_WIDTH - CARD_WIDTH) / 2;

  // Fade the map-view carousel in whenever we return to it.
  const carouselOpacity = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (isCalendarView) return;
    carouselOpacity.setValue(0);
    Animated.timing(carouselOpacity, {
      toValue: 1,
      duration: 240,
      useNativeDriver: true,
    }).start();
  }, [isCalendarView, carouselOpacity]);

  return (
    // Use flex:1 so the screen fills the tab content area
    <View style={styles.screen}>

      {/* Layer 0: Mapbox — bottom-most. Renders behind every other layer. */}
      <FomoMap />

      {/* Layer 1: neon grid overlay — pointerEvents="none" so it never blocks touches */}
      <NeonGrid />

      {/* Layer 2: SearchBar — box-none so empty space passes touches through */}
      <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
        <SearchBar
          isCalendarView={isCalendarView}
          onViewToggle={() => setIsCalendarView((v) => !v)}
        />
      </View>

      {/* Layer 3a: Map-view carousel — hidden in calendar view */}
      {!isCalendarView && (
        <Animated.View style={[styles.carouselAnchor, { opacity: carouselOpacity }]}>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            decelerationRate="fast"
            snapToInterval={CARD_WIDTH + CARD_GAP}
            snapToAlignment="center"
            contentContainerStyle={[
              styles.carouselContent,
              { paddingHorizontal: carouselPadding },
            ]}
          >
            {EVENTS.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                isActive={selectedEvent?.id === event.id}
                onPress={() => setSelectedEvent(event)}
              />
            ))}
          </ScrollView>
        </Animated.View>
      )}

      {/* Layer 3b: Calendar view — contains the date strip + event list */}
      {isCalendarView && (
        <CalendarView events={EVENTS} onEventPress={setSelectedEvent} />
      )}

      {/* Layer 4: details modal — rendered last so it sits on top of everything */}
      <EventDetails
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
      />

    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#0B0B0F',
  },
  carouselAnchor: {
    position: 'absolute',
    // Custom tab bar height ≈ 75–95px depending on safe area.
    // bottom: 116 gives a comfortable 20px gap above the tab bar on all devices.
    bottom: 116,
    left: 0,
    right: 0,
    height: 200,
  },
  carouselContent: {
    gap: CARD_GAP,
    alignItems: 'center',
  },
});
