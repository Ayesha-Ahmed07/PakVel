import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
    Alert,
    ScrollView,
    StyleSheet,
    TextInput,
    TouchableOpacity,
    View,
} from "react-native";
import { ActivityIndicator, Text } from "react-native-paper";
import { api } from "./api/axiosInstance";

export default function BrokerContactInfo() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [phone, setPhone] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    loadContactInfo();
  }, []);

  // ------------------- LOAD CONTACT INFO -------------------
  const loadContactInfo = async () => {
    try {
      const token = await AsyncStorage.getItem("token");

      const res = await api.get("/broker/contact-info", {
        headers: { Authorization: `Bearer ${token}` },
      });

      setPhone(res.data.phone || "");
      setWhatsapp(res.data.whatsapp || "");
      setEmail(res.data.email || "");

    } catch (error) {
      console.log("Load contact error:", error);
      Alert.alert("Error", "Unable to load contact info.");
    } finally {
      setLoading(false);
    }
  };

  // ------------------- SAVE CONTACT INFO -------------------
  const saveContactInfo = async () => {
    if (!phone && !whatsapp && !email) {
      Alert.alert("Missing Data", "Please enter at least one contact field.");
      return;
    }

    setSaving(true);

    try {
      const token = await AsyncStorage.getItem("token");

      await api.put(
        "/broker/contact-info",
        { phone, whatsapp, email },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      Alert.alert("Success", "Contact info updated for all itineraries.");
      router.back();

    } catch (error) {
      console.log("Save contact error:", error);
      Alert.alert("Error", "Unable to save contact info.");
    } finally {
      setSaving(false);
    }
  };

  // ------------------- LOADING UI -------------------
  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
        <Text style={{ marginTop: 10 }}>Loading contact info...</Text>
      </View>
    );
  }

  return (
    <LinearGradient
      colors={["#A7D8FF", "#7F6CFF"]}
      style={{ flex: 1, paddingTop: 60 }}
    >
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.heading}>Broker Contact Information</Text>
        <Text style={styles.subText}>
          This contact info will be shown to travelers for all your itineraries.
        </Text>

        {/* PHONE */}
        <Text style={styles.label}>Phone Number</Text>
        <TextInput
          style={styles.input}
          placeholder="03xx-xxxxxxx"
          value={phone}
          onChangeText={setPhone}
          keyboardType="phone-pad"
        />

        {/* WHATSAPP */}
        <Text style={styles.label}>WhatsApp Number</Text>
        <TextInput
          style={styles.input}
          placeholder="03xx-xxxxxxx"
          value={whatsapp}
          onChangeText={setWhatsapp}
          keyboardType="phone-pad"
        />

        {/* EMAIL */}
        <Text style={styles.label}>Email Address</Text>
        <TextInput
          style={styles.input}
          placeholder="broker@example.com"
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
        />

        {/* SAVE BUTTON */}
        <TouchableOpacity style={styles.saveBtn} onPress={saveContactInfo}>
          {saving ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.saveText}>Save Contact Info</Text>
          )}
        </TouchableOpacity>

        {/* CANCEL */}
        <TouchableOpacity
          onPress={() => router.back()}
          style={[styles.saveBtn, { backgroundColor: "#999", marginTop: 10 }]}
        >
          <Text style={styles.saveText}>Cancel</Text>
        </TouchableOpacity>
      </ScrollView>
    </LinearGradient>
  );
}

// ------------------- STYLES -------------------
const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#F7F7FF",
  },

  container: {
    backgroundColor: "rgba(255,255,255,0.15)",
    marginHorizontal: 20,
    padding: 20,
    borderRadius: 18,
    backdropFilter: "blur(6px)",
  },

  heading: {
    fontSize: 24,
    fontWeight: "800",
    color: "white",
    textAlign: "center",
    marginBottom: 10,
  },

  subText: {
    textAlign: "center",
    color: "white",
    opacity: 0.85,
    marginBottom: 25,
  },

  label: {
    color: "white",
    fontSize: 15,
    fontWeight: "700",
    marginTop: 12,
  },

  input: {
    backgroundColor: "white",
    borderRadius: 10,
    padding: 12,
    marginTop: 6,
    borderColor: "#ddd",
    borderWidth: 1,
  },

  saveBtn: {
    marginTop: 25,
    backgroundColor: "#6C3BFF",
    padding: 14,
    borderRadius: 10,
  },

  saveText: {
    color: "white",
    textAlign: "center",
    fontSize: 16,
    fontWeight: "700",
  },
});