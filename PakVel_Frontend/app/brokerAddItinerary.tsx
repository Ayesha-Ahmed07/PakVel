import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as ImagePicker from "expo-image-picker";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React, { useState } from "react";
import {
    Alert,
    Image,
    ScrollView,
    StyleSheet,
    TextInput,
    TouchableOpacity,
    View,
} from "react-native";
import { ActivityIndicator, Text } from "react-native-paper";
import { api } from "./api/axiosInstance";

export default function BrokerAddItinerary() {
  const router = useRouter();

  // ---------------- STATES ----------------
  const [title, setTitle] = useState("");
  const [departure, setDeparture] = useState("");
  const [arrival, setArrival] = useState("");

  // Dynamic locations array
  const [locations, setLocations] = useState<string[]>([""]);

  const [duration, setDuration] = useState("");
  const [price, setPrice] = useState("");

  const [coverImage, setCoverImage] = useState<string | null>(null);

  const [days, setDays] = useState<
    { day_number: number; activities: string; meals_inc: string; hotel: string }[]
  >([]);

  const [loading, setLoading] = useState(false);

  // ---------------- PICK IMAGE ----------------
  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.7,
    });

    if (!result.canceled) {
      setCoverImage(result.assets[0].uri);
    }
  };

  // ---------------- ADD DAY FIELD ----------------
  const addDay = () => {
    setDays([
      ...days,
      { day_number: days.length + 1, activities: "", meals_inc: "", hotel: "" },
    ]);
  };

  // ---------------- UPDATE DAY FIELD ----------------
  const updateDay = (index: number, field: string, value: string) => {
    const updated = [...days];
    (updated[index] as any)[field] = value;
    setDays(updated);
  };

  // ---------------- ADD NEW LOCATION ----------------
  const addLocation = () => {
    setLocations([...locations, ""]);
  };

  const updateLocation = (index: number, value: string) => {
    const updated = [...locations];
    updated[index] = value;
    setLocations(updated);
  };

  // ---------------- SUBMIT ----------------
  const submitItinerary = async () => {
    if (!title || !departure || !arrival || !duration || !price) {
      return Alert.alert("Missing Data", "Please fill all required fields.");
    }

    if (locations.some((loc) => loc.trim() === "")) {
      return Alert.alert("Missing Locations", "Please fill all location fields.");
    }

    if (days.length === 0) {
      return Alert.alert("Add Days", "You must add at least one day.");
    }

    setLoading(true);

    try {
      const token = await AsyncStorage.getItem("token");

      const payload = {
        title,
        departure_location: departure,
        arrival_location: arrival,
        trip_locations: locations, // MULTIPLE CITIES ADDED HERE
        duration_days: Number(duration),
        price_per_person: Number(price),
        description: "",
        cover_image: coverImage,
        days,
      };

      await api.post("/broker/itineraries", payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      Alert.alert("Success", "Itinerary created successfully!");
      router.replace("/brokerDashboard");
    } catch (err) {
      console.log("Add itinerary error:", err);
      Alert.alert("Error", "Failed to create itinerary.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{ flex: 1 }}>
      <LinearGradient colors={["#A7D8FF", "#7F6CFF"]} style={{ flex: 1 }}>
        {/* HEADER */}
        <View style={styles.topBar}>
          <Text style={styles.heading}>Add New Itinerary</Text>
          <TouchableOpacity onPress={() => router.back()}>
            <MaterialIcons name="arrow-back" size={26} color="white" />
          </TouchableOpacity>
        </View>

        {/* FORM */}
        <ScrollView contentContainerStyle={styles.container}>
          {/* COVER IMAGE */}
          <TouchableOpacity style={styles.imagePicker} onPress={pickImage}>
            {coverImage ? (
              <Image source={{ uri: coverImage }} style={styles.coverImage} />
            ) : (
              <Text style={styles.imagePickerText}>Pick Cover Image</Text>
            )}
          </TouchableOpacity>

          {/* TITLE */}
          <TextInput
            placeholder="Itinerary Title"
            style={styles.input}
            onChangeText={setTitle}
          />

          {/* DEPARTURE */}
          <TextInput
            placeholder="Departure Location"
            style={styles.input}
            onChangeText={setDeparture}
          />

          {/* ARRIVAL */}
          <TextInput
            placeholder="Arrival Location"
            style={styles.input}
            onChangeText={setArrival}
          />

          {/* MULTIPLE LOCATIONS */}
          <Text style={styles.sectionTitle}>Trip Locations</Text>

          {locations.map((loc, index) => (
            <TextInput
              key={index}
              placeholder={`Location ${index + 1}`}
              style={styles.input}
              value={loc}
              onChangeText={(v) => updateLocation(index, v)}
            />
          ))}

          <TouchableOpacity style={styles.addDayBtn} onPress={addLocation}>
            <MaterialIcons name="add-location-alt" size={22} color="white" />
            <Text style={styles.addDayText}>Add Another Location</Text>
          </TouchableOpacity>

          {/* DURATION */}
          <TextInput
            placeholder="Duration (Days)"
            keyboardType="numeric"
            style={styles.input}
            onChangeText={setDuration}
          />

          {/* PRICE */}
          <TextInput
            placeholder="Price Per Person (PKR)"
            keyboardType="numeric"
            style={styles.input}
            onChangeText={setPrice}
          />

          {/* DAYS SECTION */}
          <Text style={styles.sectionTitle}>Day-by-Day Plan</Text>

          {days.map((day, index) => (
            <View key={index} style={styles.dayBox}>
              <Text style={styles.dayLabel}>Day {day.day_number}</Text>

              <TextInput
                placeholder="Morning Activities"
                style={styles.dayInput}
                value={day.activities}
                onChangeText={(v) => updateDay(index, "activities", v)}
              />

              <TextInput
                placeholder="Afternoon Activities"
                style={styles.dayInput}
                value={day.meals_inc}
                onChangeText={(v) => updateDay(index, "meals_inc", v)}
              />

              <TextInput
                placeholder="Evening Activities"
                style={styles.dayInput}
                value={day.hotel}
                onChangeText={(v) => updateDay(index, "hotel", v)}
              />
            </View>
          ))}

          {/* ADD DAY */}
          <TouchableOpacity style={styles.addDayBtn} onPress={addDay}>
            <MaterialIcons name="add" size={22} color="white" />
            <Text style={styles.addDayText}>Add Day</Text>
          </TouchableOpacity>

          {/* SUBMIT */}
          {loading ? (
            <ActivityIndicator size="large" color="white" style={{ marginTop: 20 }} />
          ) : (
            <TouchableOpacity style={styles.submitBtn} onPress={submitItinerary}>
              <Text style={styles.submitText}>Save Itinerary</Text>
            </TouchableOpacity>
          )}
        </ScrollView>
      </LinearGradient>
    </View>
  );
}

/* ---------------- STYLES ---------------- */
const styles = StyleSheet.create({
  topBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 15,
  },
  heading: {
    color: "white",
    fontSize: 22,
    fontWeight: "800",
  },
  container: {
    padding: 20,
    paddingBottom: 120,
  },
  input: {
    backgroundColor: "white",
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    marginBottom: 12,
  },
  imagePicker: {
    backgroundColor: "#ffffff55",
    height: 160,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 15,
  },
  imagePickerText: {
    color: "white",
    fontSize: 16,
  },
  coverImage: {
    width: "100%",
    height: "100%",
    borderRadius: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "white",
    marginVertical: 10,
  },
  dayBox: {
    backgroundColor: "white",
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
  },
  dayLabel: {
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 8,
  },
  dayInput: {
    backgroundColor: "#f1f1f1",
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
  },
  addDayBtn: {
    flexDirection: "row",
    backgroundColor: "#6C3BFF",
    padding: 12,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
    marginVertical: 10,
  },
  addDayText: {
    color: "white",
    fontWeight: "700",
    marginLeft: 5,
  },
  submitBtn: {
    backgroundColor: "#4C35FF",
    paddingVertical: 14,
    borderRadius: 12,
    marginTop: 15,
  },
  submitText: {
    color: "white",
    fontSize: 18,
    textAlign: "center",
    fontWeight: "700",
  },
});