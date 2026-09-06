import React, { useEffect, useRef } from "react";
import { Animated, Image, StyleSheet, View } from "react-native";

export default function FadedLogo() {
  const floatAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(floatAnim, {
          toValue: -12, // float up
          duration: 1800,
          useNativeDriver: true,
        }),
        Animated.timing(floatAnim, {
          toValue: 0, // float down
          duration: 1800,
          useNativeDriver: true,
        }),
      ])
    ).start();
  }, []);

  return (
    <View style={styles.wrapper}>
      <Animated.View style={{ transform: [{ translateY: floatAnim }] }}>
        <View style={styles.logoBox}>
          <Image
            source={require("../assets/images/pakvel-logo.jpeg")}
            style={styles.logo}
            resizeMode="contain"
          />
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    justifyContent: "center",
    alignItems: "center",
  },

  logoBox: {
    width: 180,
    height: 180,
    backgroundColor: "#ffffff",
    borderRadius: 28, // smooth corners
    justifyContent: "center",
    alignItems: "center",

    // beautiful soft glow
    elevation: 10,
    shadowColor: "#6C3BFF",
    shadowOpacity: 0.2,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 6 },
  },

  logo: {
    width: 120,
    height: 120,
  },
});