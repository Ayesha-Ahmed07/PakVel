// brokerEditItinerary.tsx
import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as ImagePicker from "expo-image-picker";
import { LinearGradient } from "expo-linear-gradient";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
    Alert,
    Image,
    ImageBackground,
    ScrollView,
    StyleSheet,
    TextInput,
    TouchableOpacity,
    View,
} from "react-native";
import { ActivityIndicator, Text } from "react-native-paper";
import { api } from "./api/axiosInstance";

// ---------- TYPES ----------
type DayItem = {
  day_number: number;
  activities: string;
  meals_inc: string;
  hotel: string;
};

type DayField = "activities" | "meals_inc" | "hotel";

export default function BrokerEditItinerary() {
  const { id } = useLocalSearchParams();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // ---- LOCATIONS ----
  const [departure, setDeparture] = useState("");
  const [arrival, setArrival] = useState("");
  const [tripLocations, setTripLocations] = useState<string[]>([""]);

  const [title, setTitle] = useState("");
  const [duration, setDuration] = useState("");
  const [price, setPrice] = useState("");
  const [description, setDescription] = useState("");
  const [coverImage, setCoverImage] = useState("");
  const [isPublished, setIsPublished] = useState(false);

  const [days, setDays] = useState<DayItem[]>([]);

  // -------- LOAD ITINERARY --------
  useEffect(() => {
    loadItinerary();
  }, []);

  const loadItinerary = async () => {
    try {
      const token = await AsyncStorage.getItem("token");

      const res = await api.get(`/broker/itineraries/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const data = res.data.itinerary;

      setTitle(data.title);
      setDeparture(data.departure_location || "");
      setArrival(data.arrival_location || "");
      setTripLocations(data.trip_locations || [""]);

      setDuration(String(data.duration_days));
      setPrice(String(data.price_per_person));
      setDescription(data.description);
      setCoverImage(data.cover_image || "");
      setIsPublished(data.is_published);
      setDays(data.days || []);
    } catch (err) {
      Alert.alert("Error", "Could not load itinerary");
    } finally {
      setLoading(false);
    }
  };

  // -------- IMAGE UPLOAD --------
  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      base64: true,
      quality: 0.7,
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
    });

    if (!result.canceled) {
      setCoverImage(`data:image/jpeg;base64,${result.assets[0].base64}`);
    }
  };

  // -------- SAVE CHANGES --------
  const saveChanges = async () => {
    if (!title || !departure || !arrival)
      return Alert.alert("Missing fields", "Please fill all required fields.");

    setSaving(true);

    try {
      const token = await AsyncStorage.getItem("token");

      await api.put(
        `/broker/update-itineraries/${id}`,
        {
          title,
          departure_location: departure,
          arrival_location: arrival,
          trip_locations: tripLocations,
          duration_days: Number(duration),
          price_per_person: Number(price),
          description,
          cover_image: coverImage,
          is_published: isPublished,
          days,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      Alert.alert("Success", "Itinerary updated.");
      router.replace("/brokerDashboard");
    } catch (err) {
      Alert.alert("Error", "Could not save changes");
    } finally {
      setSaving(false);
    }
  };

  // -------- DAY LOGIC --------
  const addDay = () => {
    setDays((prev) => [
      ...prev,
      { day_number: prev.length + 1, activities: "", meals_inc: "", hotel: "" },
    ]);
  };

  const updateDay = (index: number, field: DayField, value: string) => {
    setDays((prev) =>
      prev.map((day, i) => (i === index ? { ...day, [field]: value } : day))
    );
  };

  const removeDay = (index: number) => {
    setDays((prev) =>
      prev.filter((_, i) => i !== index).map((d, i) => ({
        ...d,
        day_number: i + 1,
      }))
    );
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text>Loading itinerary...</Text>
      </View>
    );
  }

  // ============= UI START =============
  return (
    <ImageBackground
      source={require("../assets/images/pattern.jpg")}
      style={{ flex: 1 }}
      resizeMode="cover"
      imageStyle={{ opacity: 0.99 }}
    >
      <LinearGradient colors={["#9da9c899", "#ced6fc99"]} style={{ flex: 1 }}>

        {/* ----------- NAVBAR / HEADER ---------- */}
        <LinearGradient
          colors={["#58C7FF", "#6C3BFF"]}
          style={styles.header}
        >
          <TouchableOpacity
            style={styles.headerBack}
            onPress={() => router.back()}
          >
            <MaterialIcons name="arrow-back" size={26} color="white" />
          </TouchableOpacity>

          <Text style={styles.headerTitle}>Edit Itinerary</Text>
        </LinearGradient>

        {/* ----------- PAGE CONTENT ---------- */}
        <ScrollView style={styles.container}>

          {/* IMAGE */}
          <TouchableOpacity onPress={pickImage} style={styles.imageBox}>
            <Image
              source={
                coverImage
                  ? { uri: coverImage }
                  : require("../assets/images/sample-trip.png")
              }
              style={styles.image}
            />
            <View style={styles.editIcon}>
              <MaterialIcons name="edit" size={24} color="white" />
            </View>
          </TouchableOpacity>

          {/* TITLE */}
          <TextInput
            placeholder="Trip Title"
            value={title}
            onChangeText={setTitle}
            style={styles.input}
          />

          {/* LOCATIONS */}
          <Text style={styles.subHeading}>Travel Locations</Text>

          <TextInput
            placeholder="Departure Location"
            value={departure}
            onChangeText={setDeparture}
            style={styles.input}
          />

          <TextInput
            placeholder="Arrival Location"
            value={arrival}
            onChangeText={setArrival}
            style={styles.input}
          />

          {/* MULTIPLE LOCATIONS */}
          {tripLocations.map((loc, index) => (
            <View
              key={index}
              style={{ flexDirection: "row", alignItems: "center" }}
            >
              <TextInput
                placeholder={`City ${index + 1}`}
                value={loc}
                onChangeText={(t) => {
                  const updated = [...tripLocations];
                  updated[index] = t;
                  setTripLocations(updated);
                }}
                style={[styles.input, { flex: 1 }]}
              />

              <TouchableOpacity
                onPress={() =>
                  setTripLocations(tripLocations.filter((_, i) => i !== index))
                }
                style={{ marginLeft: 10 }}
              >
                <MaterialIcons name="delete" size={26} color="red" />
              </TouchableOpacity>
            </View>
          ))}

          <TouchableOpacity
            style={styles.addDayBtn}
            onPress={() => setTripLocations([...tripLocations, ""])}
          >
            <Text style={styles.addDayTxt}>+ Add Another Location</Text>
          </TouchableOpacity>

          {/* OTHER FIELDS */}
          <TextInput
            placeholder="Duration (days)"
            value={duration}
            onChangeText={setDuration}
            style={styles.input}
            keyboardType="numeric"
          />

          <TextInput
            placeholder="Price per person"
            value={price}
            onChangeText={setPrice}
            style={styles.input}
            keyboardType="numeric"
          />

          <TextInput
            placeholder="Description"
            value={description}
            onChangeText={setDescription}
            multiline
            style={[styles.input, { height: 100 }]}
          />

          {/* DAYS SECTION */}
          <Text style={styles.subHeading}>Day-wise Itinerary</Text>

          {days.map((day, index) => (
            <View key={index} style={styles.dayBox}>
              <Text style={styles.dayLabel}>Day {day.day_number}</Text>

              <TextInput
                placeholder="Morning"
                value={day.activities}
                onChangeText={(t) => updateDay(index, "activities", t)}
                style={styles.input}
              />

              <TextInput
                placeholder="Afternoon"
                value={day.meals_inc}
                onChangeText={(t) => updateDay(index, "meals_inc", t)}
                style={styles.input}
              />

              <TextInput
                placeholder="Evening"
                value={day.hotel}
                onChangeText={(t) => updateDay(index, "hotel", t)}
                style={styles.input}
              />

              <TouchableOpacity
                style={styles.removeBtn}
                onPress={() => removeDay(index)}
              >
                <Text style={styles.removeTxt}>Remove Day</Text>
              </TouchableOpacity>
            </View>
          ))}

          <TouchableOpacity style={styles.addDayBtn} onPress={addDay}>
            <Text style={styles.addDayTxt}>+ Add Day</Text>
          </TouchableOpacity>

          {/* PUBLISH TOGGLE */}
          <TouchableOpacity
            style={styles.publishToggle}
            onPress={() => setIsPublished(!isPublished)}
          >
            <MaterialIcons
              name={isPublished ? "toggle-on" : "toggle-off"}
              size={40}
              color={isPublished ? "#4CAF50" : "#777"}
            />
            <Text style={styles.publishTxt}>
              {isPublished ? "Published" : "Draft"}
            </Text>
          </TouchableOpacity>

          {/* SAVE BUTTON */}
          <TouchableOpacity style={styles.saveBtn} onPress={saveChanges}>
            {saving ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.saveTxt}>Save Changes</Text>
            )}
          </TouchableOpacity>

          <View style={{ height: 40 }} />
        </ScrollView>
      </LinearGradient>
    </ImageBackground>
  );
}

// ------------------------------------------------------------
// STYLES
// ------------------------------------------------------------
const styles = StyleSheet.create({
  header: {
    paddingTop: 55,
    paddingBottom: 20,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 25,
    borderBottomRightRadius: 25,
    marginBottom: 10,
  },
  headerBack: {
    position: "absolute",
    left: 20,
    top: 55,
  },
  headerTitle: {
    color: "white",
    fontSize: 22,
    fontWeight: "700",
    textAlign: "center",
  },

  container: { padding: 20 },

  center: { flex: 1, justifyContent: "center", alignItems: "center" },

  heading: { fontSize: 24, fontWeight: "700", marginBottom: 20 },

  imageBox: {
    width: "100%",
    height: 200,
    borderRadius: 12,
    overflow: "hidden",
    marginBottom: 15,
  },
  image: { width: "100%", height: "100%" },

  editIcon: {
    position: "absolute",
    bottom: 10,
    right: 10,
    backgroundColor: "#6C3BFF",
    padding: 8,
    borderRadius: 20,
  },

  input: {
    backgroundColor: "white",
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#ccc",
  },

  subHeading: { fontSize: 18, fontWeight: "700", marginVertical: 15 },

  dayBox: {
    backgroundColor: "#F3F3FF",
    padding: 12,
    borderRadius: 12,
    marginBottom: 15,
  },
  dayLabel: { fontSize: 16, fontWeight: "700", marginBottom: 10 },

  removeBtn: {
    backgroundColor: "#ff5252",
    padding: 8,
    borderRadius: 8,
    marginTop: 10,
  },
  removeTxt: { color: "white", textAlign: "center" },

  addDayBtn: {
    backgroundColor: "#6C3BFF",
    padding: 12,
    borderRadius: 10,
    marginBottom: 20,
  },
  addDayTxt: { color: "white", textAlign: "center", fontWeight: "700" },

  publishToggle: { flexDirection: "row", alignItems: "center", marginBottom: 25 },
  publishTxt: { marginLeft: 10, fontSize: 18 },

  saveBtn: { backgroundColor: "#4C35FF", padding: 14, borderRadius: 10 },
  saveTxt: {
    color: "white",
    textAlign: "center",
    fontSize: 18,
    fontWeight: "700",
  },
});