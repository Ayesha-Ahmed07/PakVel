import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import React from "react";
import { StyleSheet, Text, TouchableOpacity } from "react-native";
import FadedLogo from "../components/FadedLogo";

export default function Welcome() 

{
  return (
    
    <LinearGradient
      colors={["#A3D8FF", "#6C3BFF"]}
      style={styles.container}
    >
      {/* Logo */}
      < FadedLogo
      />

      {/* Title */}
      <Text style={styles.title}>Pakvel</Text>
      <Text style={styles.subtitle}>Your AI Travel Partner!</Text>

      {/* Button */}
      <TouchableOpacity style={styles.button} onPress={() => router.push("/login")}>
        <Text style={styles.buttonText}>Get Started</Text>
      </TouchableOpacity>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 30,
  },

  logo: {
    width: 170,
    height: 170,
    marginBottom: 25,
  },

  title: {
    fontSize: 32,
    fontWeight: "800",
    color: "white",
    textAlign: "center",
  },

  subtitle: {
    fontSize: 16,
    color: "#F0F0F0",
    marginTop: 8,
    marginBottom: 40,
    textAlign: "center",
  },

  button: {
    backgroundColor: "white",
    paddingVertical: 14,
    paddingHorizontal: 40,
    borderRadius: 30,
    elevation: 5,
  },

  buttonText: {
    fontSize: 18,
    fontWeight: "700",
    color: "#6C3BFF",
  },
});