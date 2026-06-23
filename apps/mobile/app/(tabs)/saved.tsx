import { Heart } from 'lucide-react-native';
import React from 'react';
import { FomoEmptyState, FomoScreen } from '../../components/ui';
import { Colors } from '../../theme';

export default function SavedScreen() {
  return (
    <FomoScreen>
      <FomoEmptyState
        icon={<Heart size={48} color={Colors.purple} strokeWidth={1.2} />}
        message="No saved events yet"
        sub={"Tap the bookmark on any event to save it here."}
      />
    </FomoScreen>
  );
}
