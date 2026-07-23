import { Search } from 'lucide-react-native';
import React from 'react';
import { FomoEmptyState, FomoScreen } from '../../components/ui';
import { usePerfScreenFocus } from '../../utils/performance-debug';
import { Colors } from '../../theme';

export default function SearchScreen() {
  usePerfScreenFocus('search');
  return (
    <FomoScreen>
      <FomoEmptyState
        icon={<Search size={48} color={Colors.purple} strokeWidth={1.2} />}
        message="Search is coming soon"
        sub="Browse events from the Discover tab for now."
      />
    </FomoScreen>
  );
}
