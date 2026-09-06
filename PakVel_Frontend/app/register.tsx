import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import React, { useState } from "react";
import {
  Alert,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import FadedLogo from "../components/FadedLogo";
import api from "./api/axiosInstance";

export default function RegisterScreen() {
  const [full_name, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // traveler / broker
  const [role, setRole] = useState<"traveler" | "broker">("traveler");

  const handleRegister = async () => {
    if (!full_name || !email || !password) {
      Alert.alert("Error", "All fields are required");
      return;
    }

    try {
      await api.post("/auth/register", {
        full_name,
        email,
        password,
        role,
      });

      if (role === "traveler") {
        Alert.alert("Success", "Account created. Please login.");
        router.replace("/login");
        return;
      }

      router.replace({
        pathname: "/brokerVerify",
        params: { email },
      });
    } catch (err: any) {
      Alert.alert(
        "Registration Failed",
        err.response?.data?.detail || "Something went wrong"
      );
    }
  };

  return (
    <LinearGradient
      colors={["#A7D8FF", "#8AA8FF", "#7F6CFF"]}
      style={styles.container}
    >
      {/* Same floating logo */}
      <FadedLogo />

      <Text style={styles.title}>Create Your Account</Text>

      {/* FORM */}
      <View style={styles.form}>
        {/* Role Selector */}
        <View style={styles.roleContainer}>
          <TouchableOpacity
            onPress={() => setRole("traveler")}
            style={[
              styles.roleBtn,
              role === "traveler" && styles.roleSelected,
            ]}
          >
            <Text
              style={[
                styles.roleTxt,
                role === "traveler" && styles.roleTxtSelected,
              ]}
            >
              Traveler
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => setRole("broker")}
            style={[
              styles.roleBtn,
              role === "broker" && styles.roleSelected,
            ]}
          >
            <Text
              style={[
                styles.roleTxt,
                role === "broker" && styles.roleTxtSelected,
              ]}
            >
              Broker
            </Text>
          </TouchableOpacity>
        </View>

        {/* Inputs */}
        <TextInput
          placeholder="Full Name/Company Name"
          style={styles.input}
          placeholderTextColor="#555"
          onChangeText={setFullName}
        />

        <TextInput
          placeholder="Email"
          style={styles.input}
          placeholderTextColor="#555"
          autoCapitalize="none"
          onChangeText={setEmail}
        />

        <TextInput
          placeholder="Password"
          secureTextEntry
          placeholderTextColor="#555"
          style={styles.input}
          onChangeText={setPassword}
        />

        {/* Register Button */}
        <TouchableOpacity style={styles.loginBtn} onPress={handleRegister}>
          <Text style={styles.loginTxt}>Register</Text>
        </TouchableOpacity>

        {/* Login Link */}
        <TouchableOpacity onPress={() => router.push("/login")}>
          <Text style={styles.registerText}>
            Already have an account?{" "}
            <Text style={{ fontWeight: "bold" }}>Login</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </LinearGradient>
  );
}

/* -------------------------------------------------------
   STYLES — EXACTLY MATCHED WITH LOGIN SCREEN
-------------------------------------------------------- */
const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    justifyContent: "center",
    alignItems: "center",
  },

  title: {
    fontSize: 28,
    fontWeight: "700",
    marginTop: 10,
    marginBottom: 25,
    color: "white",
  },

  form: {
    width: "100%",
    marginTop: 10,
  },

  roleContainer: {
    flexDirection: "row",
    justifyContent: "center",
    marginBottom: 15,
  },

  roleBtn: {
    borderWidth: 1,
    borderColor: "white",
    paddingVertical: 8,
    paddingHorizontal: 20,
    borderRadius: 25,
    marginHorizontal: 10,
  },

  roleSelected: {
    backgroundColor: "white",
  },

  roleTxt: {
    color: "white",
    fontSize: 15,
    fontWeight: "600",
  },

  roleTxtSelected: {
    color: "#6C3BFF",
    fontWeight: "700",
  },

  input: {
    height: 50,
    backgroundColor: "white",
    borderRadius: 12,
    paddingHorizontal: 15,
    fontSize: 16,
    marginVertical: 8,
  },

  loginBtn: {
    backgroundColor: "#4C35FF",
    paddingVertical: 12,
    borderRadius: 12,
    marginTop: 15,
  },

  loginTxt: {
    textAlign: "center",
    color: "white",
    fontSize: 18,
    fontWeight: "bold",
  },

  registerText: {
    marginTop: 15,
    textAlign: "center",
    color: "white",
    fontSize: 14,
  },
});