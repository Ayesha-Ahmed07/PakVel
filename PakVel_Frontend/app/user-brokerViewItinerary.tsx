import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import Slider from "@react-native-community/slider";
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

export default function UserBrokerViewItinerary() {
  const { id } = useLocalSearchParams();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [itinerary, setItinerary] = useState<any>(null);

  // ⭐ Reviews
  const [reviews, setReviews] = useState<any[]>([]);
  const [reviewCount, setReviewCount] = useState(0);
  const [alreadyReviewed, setAlreadyReviewed] = useState(false);

  // ✍️ Review modal
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [reviewModalOpen, setReviewModalOpen] = useState(false);

  // 🔥 Trip creation
  const [creatingTrip, setCreatingTrip] = useState(false);

  useEffect(() => {
    loadDetails();
    loadReviews();
  }, []);

  // ---------------- LOAD ITINERARY ----------------
  const loadDetails = async () => {
    try {
      const res = await api.get(`/broker/itineraries/${id}`);
      setItinerary(res.data.itinerary);
    } catch (err) {
      console.log("Detail error:", err);
    } finally {
      setLoading(false);
    }
  };

  // ---------------- LOAD REVIEWS ----------------
  const loadReviews = async () => {
    try {
      const res = await api.get(`/reviews/itinerary/${id}`);
      setReviews(res.data.reviews || []);
      setReviewCount(res.data.count || 0);
      if (res.data.count > 0) setAlreadyReviewed(true);
    } catch (err) {
      console.log("Review fetch error:", err);
    }
  };

  // ---------------- SUBMIT REVIEW ----------------
  const submitReview = async () => {
    try {
      setSubmitting(true);
      const token = await AsyncStorage.getItem("token");
      console.log("JWT TOOKEN:", token);

      await api.post(
        "/reviews",
        {
          itineraryId: id,
          rating,
          comment,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      Alert.alert("Success", "Review submitted successfully");
      setAlreadyReviewed(true);
      setReviewModalOpen(false);
      setComment("");
      loadReviews();
    } catch (err: any) {
      if (err?.response?.status === 400) {
        setAlreadyReviewed(true);
        setReviewModalOpen(false);
        Alert.alert(
          "Already Reviewed",
          "You’ve already submitted a review for this itinerary."
        );
      } else {
        Alert.alert("Error", "Something went wrong");
      }
    } finally {
      setSubmitting(false);
    }
  };

  // ---------------- DISCUSS WITH BROKER ----------------
  const discussWithBroker = async () => {
    try {
      setCreatingTrip(true);
      const token = await AsyncStorage.getItem("token");
      console.log("TOOKEN:", token);

      const res = await api.post(
        "/trips",
        {
          itinerary_id: id,
          trip_type: "broker",
          broker_id: itinerary.brokerId,
          destination: itinerary.arrival_location,
          budget: itinerary.price_per_person,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const tripId = res.data.trip_id;

      router.push(`/chat/${tripId}`);
    } catch (err) {
      Alert.alert("Error", "Unable to start discussion");
    } finally {
      setCreatingTrip(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text>Loading itinerary...</Text>
      </View>
    );
  }

  if (!itinerary) return <Text>No data found</Text>;

  return (
    <ImageBackground
      source={
        itinerary.cover_image
          ? { uri: itinerary.cover_image }
          : require("../assets/images/sample-trip.png")
      }
      style={{ flex: 1 }}
      imageStyle={{ opacity: 0.25 }}
    >
      <LinearGradient colors={["#9da9c899", "#ced6fc99"]} style={{ flex: 1 }}>
        {/* HEADER */}
        <LinearGradient colors={["#7F6CFF", "#A7D8FF"]} style={styles.header}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => router.back()}
          >
            <MaterialIcons name="arrow-back" size={26} color="white" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Itinerary Details</Text>
        </LinearGradient>

        <ScrollView>
          {/* IMAGE */}
          <Image
            source={
              itinerary.cover_image
                ? { uri: itinerary.cover_image }
                : require("../assets/images/sample-trip.png")
            }
            style={styles.image}
          />

          {/* MAIN INFO */}
          <View style={styles.mainBox}>
            <Text style={styles.orgName}>
              {itinerary.broker_org_name || "Independent Broker"}
            </Text>
            <Text style={styles.title}>{itinerary.title}</Text>
            <Text style={styles.subText}>
              {itinerary.departure_location} → {itinerary.arrival_location}
            </Text>
            <Text style={styles.price}>
              PKR {itinerary.price_per_person}
            </Text>
          </View>

          {/* DESCRIPTION */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Description</Text>
            <Text style={styles.sectionText}>{itinerary.description}</Text>
          </View> 

           {/* DAY SLIDER */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Day-by-Day Plan</Text>
            <ScrollView horizontal pagingEnabled showsHorizontalScrollIndicator={false}>
              {itinerary.days?.map((d: any, index: number) => (
                <View key={index} style={styles.dayCard}>
                  <Text style={styles.dayTitle}>Day {d.day_number}</Text>
                  <Text>• {d.activities}</Text>
                  <Text>• Meals: {d.meals_inc}</Text>
                  <Text>• Hotel: {d.hotel}</Text>
                </View>
              ))}
            </ScrollView>
          </View>

          {/* REVIEWS HEADER */}
          <View style={[styles.section, styles.reviewHeader]}>
            <Text style={styles.sectionTitle}>
              Reviews ({reviewCount})
            </Text>

            <TouchableOpacity
              style={[
                styles.editReviewBtn,
                alreadyReviewed && { backgroundColor: "#9CA3AF" },
              ]}
              disabled={alreadyReviewed}
              onPress={() => setReviewModalOpen(true)}
            >
              <MaterialIcons name="edit" size={20} color="white" />
            </TouchableOpacity>
          </View>

          {/* REVIEWS LIST */}
          <View style={styles.section}>
            {reviews.length === 0 ? (
              <Text style={{ color: "#666" }}>No reviews yet</Text>
            ) : (
              reviews.map((r, i) => (
                <View key={i} style={styles.reviewCard}>
                  <Text style={{ fontWeight: "700" }}>{r.user}</Text>
                  <Text>⭐ {r.rating}</Text>
                  <Text>{r.comment}</Text>
                </View>
              ))
            )}
          </View>

          <View style={{ height: 80 }} />
        </ScrollView>

        {/* REVIEW MODAL */}
        {reviewModalOpen && !alreadyReviewed && (
          <View style={styles.overlay}>
            <View style={styles.modal}>
              <Text style={styles.modalTitle}>Leave a Review</Text>

              <Text>Rating: ⭐ {rating}</Text>
              <Slider
                minimumValue={1}
                maximumValue={5}
                step={1}
                value={rating}
                onValueChange={setRating}
                minimumTrackTintColor="#6C3BFF"
                maximumTrackTintColor="#ccc"
              />

              <TextInput
                placeholder="Write your review..."
                value={comment}
                onChangeText={setComment}
                multiline
                style={styles.reviewInput}
              />

              <TouchableOpacity
                style={styles.submitBtn}
                onPress={submitReview}
                disabled={submitting}
              >
                <Text style={{ color: "white", fontWeight: "700" }}>
                  {submitting ? "Submitting..." : "Submit Review"}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={() => setReviewModalOpen(false)}>
                <Text style={{ marginTop: 10, color: "#666" }}>
                  Cancel
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* DISCUSS WITH BROKER */}
        <View style={styles.bottomBar}>
          <TouchableOpacity
            style={styles.chatBtn}
            onPress={discussWithBroker}
            disabled={creatingTrip}
          >
            <MaterialIcons name="chat" size={22} color="white" />
            <Text style={styles.chatBtnText}>
              {creatingTrip ? "Starting Chat..." : "Discuss with Broker"}
            </Text>
          </TouchableOpacity>
        </View>
      </LinearGradient>
    </ImageBackground>
  );
}

/* ---------------- STYLES ---------------- */

const styles = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center" },

  header: {
    paddingTop: 55,
    paddingBottom: 25,
    borderBottomLeftRadius: 25,
    borderBottomRightRadius: 25,
  },

  backButton: { position: "absolute", left: 20, top: 55 },

  headerTitle: {
    color: "white",
    fontSize: 22,
    fontWeight: "700",
    textAlign: "center",
  },

  dayCard: {
    backgroundColor: "white",
    padding: 12,
    borderRadius: 12,
    width: 280,
    marginRight: 15,
  },
  dayTitle: { fontWeight: "700", marginBottom: 6 },
 sectionText: { color: "#444" },
  image: {
    width: "100%",
    height: 230,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
  },

  mainBox: {
    backgroundColor: "white",
    padding: 20,
    marginHorizontal: 15,
    marginTop: -25,
    borderRadius: 15,
  },

  orgName: { fontSize: 14, color: "#6B7280", marginBottom: 4 },
  title: { fontSize: 24, fontWeight: "700" },
  subText: { color: "#555", marginTop: 6 },
  price: { marginTop: 10, fontSize: 20, fontWeight: "800", color: "#6C3BFF" },

  section: { paddingHorizontal: 20, marginTop: 25 },
  sectionTitle: { fontSize: 20, fontWeight: "700" },

  reviewHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  editReviewBtn: {
    backgroundColor: "#6C3BFF",
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
  },

  reviewCard: {
    backgroundColor: "white",
    padding: 12,
    borderRadius: 10,
    marginTop: 10,
  },

  bottomBar: {
    position: "absolute",
    bottom: 20,
    left: 20,
    right: 20,
  },

  chatBtn: {
    flexDirection: "row",
    backgroundColor: "#6C3BFF",
    padding: 16,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },

  chatBtnText: {
    color: "white",
    fontWeight: "700",
    fontSize: 16,
    marginLeft: 8,
  },

  overlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "center",
    alignItems: "center",
  },

  modal: {
    backgroundColor: "white",
    width: "85%",
    borderRadius: 14,
    padding: 16,
  },

  modalTitle: {
    fontSize: 18,
    fontWeight: "800",
    marginBottom: 10,
  },

  reviewInput: {
    backgroundColor: "#f1f1f1",
    borderRadius: 8,
    padding: 10,
    marginTop: 10,
    height: 80,
  },

  submitBtn: {
    backgroundColor: "#6C3BFF",
    padding: 12,
    borderRadius: 10,
    alignItems: "center",
    marginTop: 12,
  },
});