import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import React, { useState } from "react";
import {
  Alert,
  Modal,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import FadedLogo from "../components/FadedLogo";
import api from "./api/axiosInstance";

// ✅ Your Google Web Client ID (ONLY Web Client)
const WEB_CLIENT_ID =
  "979370922007-sdbjf67nmk2b64aqqojdb5cedsmv246c.apps.googleusercontent.com";

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [tempGoogleToken, setTempGoogleToken] = useState("");
  const [roleModalVisible, setRoleModalVisible] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // ------------------- MANUAL LOGIN -------------------
  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert("Error", "Please fill all fields");
      return;
    }

    try {
      const response = await api.post("/auth/login", { email, password });
      const { access_token, role } = response.data;

      await AsyncStorage.setItem("token", access_token);
      await AsyncStorage.setItem("role", role);
      if(role === "broker"){
        router.replace("/brokerDashboard");
      } else {
        router.replace("/dashboard");
      }
    } catch (error: any) {
      Alert.alert(
        "Login Failed",
        error.response?.data?.detail || "Something went wrong"
      );
    }
  };

  // ------------------- GOOGLE LOGIN (Expo SDK 54) -------------------
  //const startGoogleLogin = async () => {
  //  try {
  //    // Auto-generated secure redirect URI via Expo proxy
  //    const redirectUri = AuthSession.makeRedirectUri({ useProxy: true });

      // Create an OAuth request
  //    const request = new AuthSession.AuthRequest({
  //      clientId: WEB_CLIENT_ID,
  //      redirectUri,
  //      responseType: "id_token",
  //      scopes: ["openid", "email", "profile"],
  //      extraParams: { nonce: "pakvel_nonce_123" }, // Google requires nonce
  //    });

      // Build Google authorization URL
   //   const authUrl = await request.makeAuthUrlAsync({
  //      authorizationEndpoint: "https://accounts.google.com/o/oauth2/v2/auth",
  //    });

      // Open Google login window
  //    const result = await AuthSession.startAsync({
  //      authUrl,
   //     returnUrl: redirectUri,
   //   });

  //    // User cancelled or failed
  //    if (result.type !== "success") return;

      // Extract Google ID token
  //    const idToken = (result.params as any).id_token;

  //    if (!idToken) {
  //      Alert.alert("Google Login Failed", "Google returned no id_token.");
  //      return;
  //    }

      // Store token temporarily → will send to backend after role selection
  //    setTempGoogleToken(idToken);
  //    setRoleModalVisible(true);
  //  } catch (err) {
  //    console.log(err);
  //    Alert.alert("Google Login Error", "Something went wrong");
  //  }
  //};

  // ------------------- FINALIZE GOOGLE LOGIN (Send to Backend) -------------------
  const finalizeGoogleLogin = async (role: "traveler" | "broker") => {
    try {
      const res = await api.post("/auth/google/mobile", {
        id_token: tempGoogleToken,
        role,
      });

      const { access_token } = res.data;

      await AsyncStorage.setItem("token", access_token);
      setRoleModalVisible(false);

      if (role === "broker") {
        router.replace("/brokerVerify");
      } else {
        router.replace("/dashboard");
      }
    } catch (err) {
      console.log(err);
      Alert.alert("Google Login Error", "Something went wrong on server");
    }
  };

  return (
    <LinearGradient
      colors={["#A7D8FF", "#8AA8FF", "#7F6CFF"]}
      style={styles.container}
    >
      {/* Floating logo */}
      <FadedLogo />

      <Text style={styles.title}>Login to Pakvel</Text>

      {/* FORM */}
      <View style={styles.form}>
        <TextInput
          placeholder="Email"
          style={styles.input}
          placeholderTextColor="#555"
          onChangeText={setEmail}
        />

        <View style={styles.passwordContainer}>
  <TextInput
    placeholder="Password"
    secureTextEntry={!showPassword}
    placeholderTextColor="#555"
    style={styles.passwordInput}
    onChangeText={setPassword}
  />

  <TouchableOpacity
    onPress={() => setShowPassword(!showPassword)}
    style={styles.eyeBtn}
  >
    <Text>{showPassword ? "🙈" : "👁️"}</Text>
  </TouchableOpacity>
</View>

        {/* Login Button */}
        <TouchableOpacity style={styles.loginBtn} onPress={handleLogin}>
          <Text style={styles.loginText}>Login</Text>
        </TouchableOpacity>

        {/* Register Link */}
        <TouchableOpacity onPress={() => router.push("/register")}>
          <Text style={styles.registerText}>
            Don't have an account?{" "}
            <Text style={{ fontWeight: "bold" }}>Register</Text>
          </Text>
        </TouchableOpacity>

        {/* Google Login Button
        <TouchableOpacity style={styles.googleBtn} onPress={startGoogleLogin}>
         <AntDesign name="google" size={20} color="white" />
          <Text style={styles.googleText}>Continue with Google</Text>
        </TouchableOpacity>
        */}
      </View>

      {/* ROLE SELECTION MODAL */}
      <Modal transparent visible={roleModalVisible} animationType="slide">
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Continue as</Text>

            <TouchableOpacity
              style={styles.roleBtn}
              onPress={() => finalizeGoogleLogin("traveler")}
            >
              <Text style={styles.roleBtnText}>Traveler 🧳</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.roleBtn}
              onPress={() => finalizeGoogleLogin("broker")}
            >
              <Text style={styles.roleBtnText}>Broker 🧑‍💼</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.cancelBtn}
              onPress={() => setRoleModalVisible(false)}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    justifyContent: "center",
    alignItems: "center",
  },

  title: {
    fontSize: 28,
    fontWeight: "bold",
    marginTop: 10,
    marginBottom: 25,
    color: "white",
  },

  form: {
    width: "100%",
    marginTop: 10,
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
    marginTop: 10,
  },

  loginText: {
    color: "white",
    fontSize: 18,
    textAlign: "center",
    fontWeight: "bold",
  },

  registerText: {
    marginTop: 15,
    textAlign: "center",
    color: "white",
    fontSize: 14,
  },

  googleBtn: {
    flexDirection: "row",
    backgroundColor: "#4285F4",
    padding: 12,
    borderRadius: 12,
    marginTop: 18,
    alignItems: "center",
    justifyContent: "center",
  },

  googleText: {
    color: "white",
    fontWeight: "600",
    marginLeft: 10,
  },

  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "flex-end",
  },

  modalCard: {
    backgroundColor: "white",
    padding: 25,
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
  },

  modalTitle: {
    fontSize: 20,
    fontWeight: "bold",
    textAlign: "center",
    marginBottom: 20,
  },

  roleBtn: {
    padding: 14,
    backgroundColor: "#ECEBFF",
    borderRadius: 12,
    marginBottom: 12,
  },

  roleBtnText: {
    fontSize: 18,
    textAlign: "center",
    color: "#6C3BFF",
    fontWeight: "bold",
  },

  cancelBtn: {
    padding: 12,
    marginTop: 5,
  },

  cancelText: {
    textAlign: "center",
    color: "#777",
    fontSize: 16,
  },
  passwordContainer: {
  flexDirection: "row",
  alignItems: "center",
  backgroundColor: "white",
  borderRadius: 12,
  marginVertical: 8,
},

passwordInput: {
  flex: 1,
  height: 50,
  paddingHorizontal: 15,
  fontSize: 16,
},

eyeBtn: {
  paddingHorizontal: 12,
},
});