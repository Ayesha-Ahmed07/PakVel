import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import {
  ImageBackground,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  View,
} from "react-native";
import { ActivityIndicator, Chip, Text, TextInput } from "react-native-paper";
import styled from "styled-components/native";
import { api } from "./api/axiosInstance";

// ---------- Styled Components ----------
const Screen = styled.View`
  flex: 1;
`;

const SectionLabel = styled(Text)`
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 6px;
  margin-top: 14px;
  color: #111827;
`;

const ChipGrid = styled.View`
  flex-direction: row;
  flex-wrap: wrap;
`;

// ---------- Main Component ----------
export default function CreateTrip() {
  const router = useRouter();

  const [fromCity, setFromCity] = useState("");
  const [toCity, setToCity] = useState("");
  const [duration, setDuration] = useState("3");
  const [budget, setBudget] = useState("moderate");
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const interests = [
    "Adventure",
    "Culture",
    "Historical",
    "Food",
    "Nature",
    "Relaxation",
    "Shopping",
  ];

  const toggleInterest = (item: string) => {
    setSelectedInterests((prev) =>
      prev.includes(item) ? prev.filter((i) => i !== item) : [...prev, item]
    );
  };

  const createItinerary = async () => {
    if (!fromCity.trim() || !toCity.trim()) {
      alert("Please enter both From and To cities!");
      return;
    }

    setLoading(true);

    try {
      const token = await AsyncStorage.getItem("token");

      await api.post(
        "/traveler/preferences",
        {
          destination: toCity,
          departure: fromCity,
          duration,
          budget,
          interests: selectedInterests,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const itineraryRes = await api.post(
        "/traveler/generate-itinerary",
        {
          destination: toCity,
          departure: fromCity,
          duration,
          budget,
          interests: selectedInterests,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      router.push(`/itinerary/${itineraryRes.data.itinerary._id}`);
    } catch (err) {
      console.log("Create trip error:", err);
      alert("Something went wrong!");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen>
      {/* Vibrant background */}
      <ImageBackground
        source={require("../assets/images/pattern.jpg")}
        style={{ flex: 1, width: "100%", height: "100%" }}
        resizeMode="cover"
        imageStyle={{
          width: "100%",
          height: "100%",
          resizeMode: "cover",
          opacity: 0.99,
        }}
      >
        {/* Overlay gradient */}
        <LinearGradient
          colors={["#2d4888cc", "#4e5a6ecc", "#cca6cccc"]}
          style={{ flex: 1 }}
        >
          {/* TOP NAVBAR */}
          <LinearGradient
            colors={["#58C7FF", "#6C3BFF"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.header}
          >
            {/* BACK BUTTON */}
            <TouchableOpacity
              style={styles.backBtn}
              onPress={() => router.replace("/dashboard")}
            >
              <MaterialIcons name="arrow-back" size={28} color="white" />
            </TouchableOpacity>

            <Text style={styles.appTitle}>Create Trip</Text>
          </LinearGradient>

          {/* FORM CONTENT */}
          <ScrollView contentContainerStyle={styles.scrollContent}>
            <View style={styles.formCard}>
              {/* FROM CITY */}
              <SectionLabel>From</SectionLabel>
              <TextInput
                value={fromCity}
                onChangeText={setFromCity}
                mode="outlined"
                placeholder="Departure city e.g. Karachi"
                style={styles.input}
                outlineStyle={styles.inputOutline}
                activeOutlineColor="#6C3BFF"
              />

              {/* TO CITY */}
              <SectionLabel>To</SectionLabel>
              <TextInput
                value={toCity}
                onChangeText={setToCity}
                mode="outlined"
                placeholder="Arrival city e.g. Hunza"
                style={styles.input}
                outlineStyle={styles.inputOutline}
                activeOutlineColor="#6C3BFF"
              />

              {/* Duration */}
              <SectionLabel>Duration (Days)</SectionLabel>
              <TextInput
                value={duration}
                onChangeText={setDuration}
                keyboardType="numeric"
                mode="outlined"
                style={styles.input}
                outlineStyle={styles.inputOutline}
                activeOutlineColor="#6C3BFF"
              />

              {/* Budget */}
              <SectionLabel>Budget</SectionLabel>
              <View style={styles.budgetRow}>
                {[
                  { label: "Low", value: "low" },
                  { label: "Moderate", value: "moderate" },
                  { label: "High", value: "high" },
                ].map((option) => {
                  const isActive = budget === option.value;
                  return (
                    <Chip
                      key={option.label}
                      onPress={() => setBudget(option.value)}
                      style={[styles.chip, isActive && styles.chipActive]}
                      textStyle={[
                        styles.chipText,
                        isActive && styles.chipTextActive,
                      ]}
                    >
                      {option.label}
                    </Chip>
                  );
                })}
              </View>

              {/* Interests */}
              <SectionLabel>Your Interests</SectionLabel>
              <ChipGrid>
                {interests.map((item) => {
                  const isSelected = selectedInterests.includes(item);
                  return (
                    <Chip
                      key={item}
                      onPress={() => toggleInterest(item)}
                      style={[
                        styles.interestChip,
                        isSelected && styles.interestChipActive,
                      ]}
                      textStyle={[
                        styles.interestText,
                        isSelected && styles.interestTextActive,
                      ]}
                    >
                      {item}
                    </Chip>
                  );
                })}
              </ChipGrid>

              {/* BUTTON */}
              {loading ? (
                <ActivityIndicator
                  size="large"
                  color="#6C3BFF"
                  style={{ marginTop: 26 }}
                />
              ) : (
                <LinearGradient
                  colors={["#6C3BFF", "#8B5CF6"]}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                  style={styles.buttonGradient}
                >
                  <TouchableOpacity onPress={createItinerary}>
                    <View style={styles.buttonInner}>
                      <Text style={styles.buttonText}>Generate Itinerary</Text>
                    </View>
                  </TouchableOpacity>
                </LinearGradient>
              )}
            </View>

            <Text style={styles.hintText}>
              Start your Adventure with a Tap! ✨
            </Text>
          </ScrollView>
        </LinearGradient>
      </ImageBackground>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: {
    paddingTop: 42,
    paddingBottom: 24,
    alignItems: "center",
    borderBottomLeftRadius: 22,
    borderBottomRightRadius: 22,
    elevation: 8,
    shadowColor: "#000",
    shadowOpacity: 0.25,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },

  backBtn: {
    position: "absolute",
    left: 20,
    top: 45,
    padding: 6,
    zIndex: 10,
  },

  appTitle: {
    color: "white",
    fontSize: 26,
    fontWeight: "900",
    letterSpacing: 1,
  },

  scrollContent: {
    padding: 18,
    paddingBottom: 40,
  },

  formCard: {
    backgroundColor: "rgba(255,255,255,0.96)",
    borderRadius: 22,
    padding: 18,
    shadowColor: "#000",
    shadowOpacity: 0.18,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 8,
  },

  input: {
    backgroundColor: "#f9fafb",
    borderRadius: 14,
    marginBottom: 10,
  },

  inputOutline: {
    borderRadius: 14,
    borderColor: "#d1d5db",
    borderWidth: 1.2,
  },

  budgetRow: {
    flexDirection: "row",
    marginBottom: 6,
  },

  chip: {
    marginRight: 8,
    marginBottom: 8,
    backgroundColor: "#E5E7EB",
    borderRadius: 20,
  },
  chipActive: {
    backgroundColor: "#6C3BFF",
  },
  chipText: {
    color: "#111827",
    fontWeight: "600",
  },
  chipTextActive: {
    color: "white",
  },

  interestChip: {
    backgroundColor: "#E5E7EB",
    borderRadius: 18,
    paddingHorizontal: 6,
    marginRight: 8,
    marginBottom: 10,
  },
  interestChipActive: {
    backgroundColor: "#8B5CF6",
  },
  interestText: {
    color: "#111827",
    fontSize: 13,
    fontWeight: "600",
  },
  interestTextActive: {
    color: "white",
  },

  buttonGradient: {
    borderRadius: 16,
    marginTop: 22,
    elevation: 5,
    shadowColor: "#000",
    shadowOpacity: 0.25,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },

  buttonInner: {
    paddingVertical: 14,
    alignItems: "center",
  },

  buttonText: {
    color: "white",
    fontSize: 17,
    fontWeight: "700",
  },

  hintText: {
    color: "#e5e7eb",
    fontSize: 12,
    textAlign: "center",
    marginTop: 10,
    opacity: 0.9,
  },
});