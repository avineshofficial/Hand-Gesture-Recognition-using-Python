import React, {useRef, useState, useEffect} from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  Alert,
  StatusBar,
  Dimensions,
  Vibration,
} from 'react-native';
import {
  Gesture,
  GestureDetector,
  GestureHandlerRootView,
} from 'react-native-gesture-handler';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  runOnJS, // <-- 1. IMPORT runOnJS HERE
} from 'react-native-reanimated';

const {width} = Dimensions.get('window');
const JOYSTICK_AREA_SIZE = width * 0.6;
const JOYSTICK_SIZE = JOYSTICK_AREA_SIZE * 0.4;
const JOYSTICK_MAX_OFFSET = (JOYSTICK_AREA_SIZE - JOYSTICK_SIZE) / 2;

function App(): React.JSX.Element {
  const [ipAddress, setIpAddress] = useState('10.2.21.49'); // Default IP
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const isDragging = useSharedValue(false);

  // Joystick position
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);

  // Scroll position
  const scrollY = useSharedValue(0);

  // Function to send data over WebSocket
  const sendWsMessage = (data: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    }
  };

  // Server connection logic
  const connectToServer = () => {
    if (isConnected) {
      ws.current?.close();
      return;
    }
    if (!ipAddress) {
      Alert.alert('Error', 'Please enter a valid IP Address.');
      return;
    }
    const serverUrl = `ws://${ipAddress}:8765`;
    ws.current = new WebSocket(serverUrl);
    ws.current.onopen = () => setIsConnected(true);
    ws.current.onclose = () => setIsConnected(false);
    ws.current.onerror = () => {
      Alert.alert('Connection Error', `Could not connect to ${serverUrl}.`);
      setIsConnected(false);
    };
  };

  // Joystick gesture handler
  const joystickPan = Gesture.Pan()
    .onUpdate(event => {
      'worklet';
      const distance = Math.sqrt(event.translationX ** 2 + event.translationY ** 2);
      if (distance <= JOYSTICK_MAX_OFFSET) {
        translateX.value = event.translationX;
        translateY.value = event.translationY;
      } else {
        translateX.value = (event.translationX / distance) * JOYSTICK_MAX_OFFSET;
        translateY.value = (event.translationY / distance) * JOYSTICK_MAX_OFFSET;
      }
      // 2. USE runOnJS DIRECTLY
      runOnJS(sendWsMessage)({action: 'move', x: translateX.value, y: translateY.value});
    })
    .onEnd(() => {
      'worklet';
      translateX.value = withSpring(0);
      translateY.value = withSpring(0);
    });

  // Scroll gesture handler
  const scrollPan = Gesture.Pan()
    .onUpdate(event => {
      'worklet';
      scrollY.value = event.translationY;
      // 2. USE runOnJS DIRECTLY
      runOnJS(sendWsMessage)({action: 'scroll', y: event.translationY});
    })
    .onEnd(() => {
      'worklet';
      scrollY.value = withSpring(0);
    });
  
  // Drag button handler
  const handleDragPress = () => {
    isDragging.value = !isDragging.value;
    sendWsMessage({ action: isDragging.value ? 'drag_start' : 'drag_end' });
    Vibration.vibrate(50);
  };
  
  const animatedJoystickStyle = useAnimatedStyle(() => ({
    transform: [{translateX: translateX.value}, {translateY: translateY.value}],
  }));

  const animatedDragButtonStyle = useAnimatedStyle(() => ({
    backgroundColor: isDragging.value ? '#0056b3' : '#007bff',
    transform: [{ scale: isDragging.value ? 1.05 : 1 }],
  }));

  return (
    <GestureHandlerRootView style={styles.container}>
      <StatusBar barStyle="light-content" />
      
      {!isConnected ? (
        <View style={styles.connectionOverlay}>
            <Text style={styles.label}>PC Server IP Address:</Text>
            <TextInput style={styles.input} onChangeText={setIpAddress} value={ipAddress} />
            <TouchableOpacity style={styles.connectButton} onPress={connectToServer}>
              <Text style={styles.buttonText}>CONNECT</Text>
            </TouchableOpacity>
        </View>
      ) : (
        <>
          <View style={styles.mainArea}>
            <View style={styles.joystickContainer}>
              <GestureDetector gesture={joystickPan}>
                <View style={styles.joystickBase}>
                  <Animated.View style={[styles.joystickHandle, animatedJoystickStyle]} />
                </View>
              </GestureDetector>
            </View>
            <GestureDetector gesture={scrollPan}>
              <View style={styles.scrollArea}>
                <Text style={styles.scrollText}>SCROLL</Text>
              </View>
            </GestureDetector>
          </View>

          <View style={styles.buttonRow}>
            <TouchableOpacity style={styles.actionButton} onPress={() => sendWsMessage({action: 'left_click'})}>
              <Text style={styles.buttonText}>Left</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionButton} onPress={() => sendWsMessage({action: 'right_click'})}>
              <Text style={styles.buttonText}>Right</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.actionButton} onPress={() => sendWsMessage({action: 'double_click'})}>
              <Text style={styles.buttonText}>Double</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity onPress={handleDragPress}>
            <Animated.View style={[styles.dragButton, animatedDragButtonStyle]}>
              <Text style={styles.buttonText}>{isDragging.value ? 'RELEASE DRAG' : 'HOLD DRAG'}</Text>
            </Animated.View>
          </TouchableOpacity>
        </>
      )}
    </GestureHandlerRootView>
  );
}

// ... (The styles block at the bottom remains the same)
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1c1c1e',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  connectionOverlay: { width: '100%' },
  label: { color: 'white', fontSize: 16, marginBottom: 10, textAlign: 'center' },
  input: {
    backgroundColor: '#3a3a3c',
    color: 'white',
    borderRadius: 8,
    padding: 15,
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 20,
  },
  connectButton: {
    backgroundColor: '#0a84ff',
    padding: 20,
    borderRadius: 8,
    alignItems: 'center',
  },
  mainArea: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
  },
  joystickContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  joystickBase: {
    width: JOYSTICK_AREA_SIZE,
    height: JOYSTICK_AREA_SIZE,
    borderRadius: JOYSTICK_AREA_SIZE / 2,
    backgroundColor: '#3a3a3c',
    justifyContent: 'center',
    alignItems: 'center',
  },
  joystickHandle: {
    width: JOYSTICK_SIZE,
    height: JOYSTICK_SIZE,
    borderRadius: JOYSTICK_SIZE / 2,
    backgroundColor: '#28a745',
  },
  scrollArea: {
    width: width * 0.2,
    height: '80%',
    backgroundColor: '#3a3a3c',
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollText: {
    color: '#8e8e93',
    fontWeight: 'bold',
    transform: [{rotate: '90deg'}],
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    width: '100%',
    marginVertical: 20,
  },
  actionButton: {
    backgroundColor: '#3a3a3c',
    paddingVertical: 15,
    paddingHorizontal: 25,
    borderRadius: 8,
  },
  dragButton: {
    backgroundColor: '#007bff',
    width: '100%',
    padding: 20,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default App;