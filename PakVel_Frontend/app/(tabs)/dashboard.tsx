//app/(tabs)/dashboard.tsx
import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  Dimensions,
  Image,
  ImageBackground,
  Modal,
  ScrollView,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { ActivityIndicator, Card, Text } from "react-native-paper";
import styled from "styled-components/native";
import { api } from "../api/axiosInstance";

// ---------------- Types ----------------
interface Trip {
  _id: string;
  destination: string;
  duration: number;
  budget: string;
}

// ---------------- Styled Components ----------------
const ScreenWrapper = styled.View`
  flex: 1;
`;

const Content = styled.ScrollView`
  padding: 20px;
`;

const SectionTitle = styled(Text)`
  font-size: 22px;
  font-weight: 700;
  margin-top: 25px;
  margin-bottom: 8px;
`;

// Frosted Section Background
const FrostedSection = styled.View`
  background-color: rgba(255, 255, 255, 0.55);
  padding: 10px;
  border-radius: 18px;
  margin-top: 10px;
`;

// Trip Card
const TripCardContainer = styled.TouchableOpacity`
  flex-direction: row;
  background-color: rgba(255, 255, 255, 0.85);
  border-radius: 14px;
  padding: 10px;
  margin-bottom: 14px;
  elevation: 3;
`;

const TripImage = styled(Image)`
  width: 90px;
  height: 90px;
  border-radius: 12px;
  margin-right: 12px;
`;

// ------- Hero slider data -------
const HERO_SLIDES = [
  {
    id: "Hunza Valley",
    title: "Hunza Valley",
    subtitle: "Nature's Paradise",
    image: require("../../assets/images/hunza.jpg"),
  },
  {
    id: "Malamjabba",
    title: "Skiing in Malamjabba",
    subtitle: "Swat's snowy paradise",
    image: require("../../assets/images/malamjabba.jpg"),
  },
  {
    id: "kashmir",
    title: "Highlands of kashmir",
    subtitle: "Spring in tulip garden",
    image: require("../../assets/images/kashmir.png"),
  },
  {
    id: "skardu",
    title: "Magical Skardu",
    subtitle: "Land of lakes, mountains and serenity",
    image: require("../../assets/images/skardu.jpg"),
  },
];

const { width: SCREEN_WIDTH } = Dimensions.get("window");
const HERO_CARD_WIDTH = SCREEN_WIDTH - 40;

// ---------------- City Image Mapper ----------------
const cityImages: Record<string, any> = {
  quetta: require("../../assets/images/Quetta.png"),
  islamabad: require("../../assets/images/islamabad.jpg"),
  hyderabad: require("../../assets/images/hyderabad.png"),
   karachi: require("../../assets/images/karachi.jpg"),
  lahore: require("../../assets/images/lahore.jpg"),
  faislabad: require("../../assets/images/faislabad.jpg"),
  chitral: require("../../assets/images/chitral.jpg"),
  hunza: require("../../assets/images/hunza.jpg"),
  kashmir: require("../../assets/images/kashmir.png"),
  malamjabba: require("../../assets/images/malamjabba.jpg"),
};

const getCityImage = (city: string) => {
  const key = city.trim().toLowerCase();
  return cityImages[key] || require("../../assets/images/sample-trip.png");
};

// ---------------- Component -------------------
export default function Dashboard() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [myTrips, setMyTrips] = useState<Trip[]>([]);
  const [suggested, setSuggested] = useState<Trip[]>([]);
  const [activeSlide, setActiveSlide] = useState(0);
  const [showSidebar, setShowSidebar] = useState(false);
  const [reviewTrip, setReviewTrip] = useState<any | null>(null);
const [reviewModalOpen, setReviewModalOpen] = useState(false);
const [rating, setRating] = useState(5);
const [comment, setComment] = useState("");
const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadDashboard();
    loadReviewPending();
  }, []);

  const loadDashboard = async () => {
    try {
      const token = await AsyncStorage.getItem("token");
      if (!token) {
        router.replace("/login");
        return;
      }
      const res = await api.get("/traveler/dashboard", {
        headers: { Authorization: `Bearer ${token}` },
      });

      setMyTrips(res.data.my_trips);
      setSuggested(res.data.suggested_trips);
    } catch (err) {
      console.log("Dashboard error:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadReviewPending = async () => {
  try {
    const token = await AsyncStorage.getItem("token");

    const res = await api.get(
      "/trips/completed/review-pending",
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    if (res.data.hasReviewPending) {
      setReviewTrip(res.data.trip);
    } else {
      setReviewTrip(null);
    }
  } catch (err) {
    console.log("Review pending error:", err);
  }
};

const submitReview = async () => {
  try {
    const token = await AsyncStorage.getItem("token");

    await api.post(
      "/reviews/",
      {
        itineraryId: reviewTrip?.itinerary_source_id,
        rating,
        comment,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );

    alert("Review submitted successfully");

    setReviewModalOpen(false);
    setReviewTrip(null); // 👈 remove banner
    setComment("");

  } catch (err: any) {
    alert(err?.response?.data?.detail || "Review failed");
  } finally {
    setSubmitting(false);
  }
};
  


  if (loading) {
    return (
      <LinearGradient colors={["#F8FAFF", "#EDF0FF"]} style={{ flex: 1 }}>
        <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
          <ActivityIndicator size="large" />
          <Text style={{ marginTop: 10 }}>Loading Dashboard...</Text>
        </View>
      </LinearGradient>
    );
  }

  return (
    <ScreenWrapper>

      {/* GLOBAL BACKGROUND IMAGE */}
      <ImageBackground
        source={require("../../assets/images/pattern.jpg")}
        style={{ flex: 1,
          width: "100%",
          height: "100%",
         }}
        resizeMode="cover"
        imageStyle={{ width: "100%",
          height: "100%",
          resizeMode: "cover",
          opacity: 0.99, }} // Soft global scenic background
      >

        {/* SOFT PAGE GRADIENT OVERLAY */}
        <LinearGradient colors={["#9da9c899", "#ced6fc99"]} style={{ flex: 1 }}>

          {/* TOP BAR */}
          <LinearGradient
            colors={["#58C7FF", "#6C3BFF"]}
            style={{
              paddingTop: 40,
              paddingBottom: 20,
              alignItems: "center",
              justifyContent: "center",
              borderBottomLeftRadius: 18,
              borderBottomRightRadius: 18,
              elevation: 5,
              position: "relative",
            }}
          >
            {/* SIDEBAR BUTTON */}
<TouchableOpacity
  onPress={() => setShowSidebar(true)}
  style={{
    position: "absolute",
    left: 20,
    top: 45,
    padding: 6,
  }}
>
  <MaterialIcons name="menu" size={28} color="white" />
</TouchableOpacity>
            <Text style={{ color: "white", fontSize: 26, fontWeight: "800" }}>
              Pakvel
            </Text>
            {/* LOGOUT BUTTON */}
<TouchableOpacity
  onPress={async () => {
    await AsyncStorage.removeItem("token");
    router.replace("/login");
  }}
  style={{
    position: "absolute",
    right: 20,
    top: 45,
    padding: 6,
  }}
>
  <MaterialIcons name="logout" size={26} color="white" />
</TouchableOpacity>
          </LinearGradient>

          {/* MAIN CONTENT */}
          <Content>
            <SectionTitle>Places you can visit</SectionTitle>

            {/* HERO SLIDER IN ROUNDED CONTAINER */}
            <View
              style={{ marginBottom: 10,
              }}
            >
              <ScrollView
                horizontal
                pagingEnabled
                showsHorizontalScrollIndicator={false}
                snapToAlignment="center"
                decelerationRate="fast"
                scrollEventThrottle={16}
                onScroll={(event) => {
                  const index = Math.round(
                    event.nativeEvent.contentOffset.x / HERO_CARD_WIDTH
                  );
                  setActiveSlide(index);
                }}
              >
                {HERO_SLIDES.map((slide) => (
                  <View
                    key={slide.id}
                    style={{
                      width: HERO_CARD_WIDTH,
                      height: 180,
                      marginRight: 12,
                      borderRadius: 18,
                      overflow: "hidden",
                    }}
                  >
                    <ImageBackground
                      source={slide.image}
                      style={{ flex: 1, justifyContent: "flex-end" }}
                      resizeMode="cover"
                    >
                      <LinearGradient
                        colors={["rgba(0,0,0,0.05)", "rgba(0,0,0,0.45)"]}
                        style={{ flex: 1, padding: 16, justifyContent: "flex-end" }}
                      >
                        <Text style={{ color: "white", fontSize: 20, fontWeight: "800" }}>
                          {slide.title}
                        </Text>
                        <Text style={{ color: "#E5E7EB", marginTop: 4, fontSize: 13 }}>
                          {slide.subtitle}
                        </Text>
                      </LinearGradient>
                    </ImageBackground>
                  </View>
                ))}
              </ScrollView>

              {/* DOTS */}
              <View style={{ flexDirection: "row", justifyContent: "center", marginTop: 8 }}>
                {HERO_SLIDES.map((_, index) => (
                  <View
                    key={index}
                    style={{
                      width: index === activeSlide ? 16 : 6,
                      height: 6,
                      borderRadius: 3,
                      backgroundColor: index === activeSlide ? "#6C3BFF" : "#CBD5F5",
                      marginHorizontal: 4,
                    }}
                  />
                ))}
              </View>
            </View>

{reviewTrip && (
  <TouchableOpacity
    onPress={() => setReviewModalOpen(true)}
    style={{
      backgroundColor: "#16A34A",
      padding: 14,
      borderRadius: 16,
      marginBottom: 12,
    }}
  >
    <Text style={{ color: "white", fontWeight: "800" }}>
      🎉 {reviewTrip.destination} trip completed!
    </Text>
    <Text style={{ color: "white", marginTop: 4 }}>
      Tap to leave a review
    </Text>
  </TouchableOpacity>
)}

            {/* MY TRIPS — FROSTED CONTAINER */}
            <SectionTitle>My Trips</SectionTitle>
            <FrostedSection>
              {myTrips.length === 0 ? (
                <Text style={{ color: "#6B7280" }}>
                  No trips yet. Generate your first itinerary!
                </Text>
              ) : (
                myTrips.map((trip) => (
                  <TripCardContainer
                    key={trip._id}
                    onPress={() => router.push(`/itinerary/${trip._id}`)}
                  >
                    <TripImage source={getCityImage(trip.destination)} />
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 16, fontWeight: "700" }}>
                        {trip.destination}
                      </Text>
                      <Text style={{ color: "#6b7280", marginTop: 4 }}>
                        {trip.duration} Days •  {trip.budget?.charAt(0).toUpperCase() + trip.budget?.slice(1)}
                      </Text>
                    </View>
                  </TripCardContainer>
                ))
              )}
            </FrostedSection>

            {/* SUGGESTED ITINERARIES — FROSTED */}
            <SectionTitle>Suggested Itineraries</SectionTitle>
            <FrostedSection>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {suggested.map((item) => (
                  <TouchableOpacity
                    key={item._id}
                    onPress={() => router.push(`/itinerary/${item._id}`)}
                  >
                    <Card
                      style={{
                        width: 180,
                        marginRight: 14,
                        borderRadius: 16,
                        overflow: "hidden",
                        backgroundColor: "rgba(255,255,255,0.85)",
                      }}
                    >
                      <Image
                        source={getCityImage(item.destination)}
                        style={{ width: "100%", height: 110 }}
                      />
                      <Card.Content>
                        <Text style={{ fontSize: 17, fontWeight: "600" }}>
                          {item.destination}
                        </Text>
                        <Text style={{ color: "#6b7280", marginTop: 4 }}>
                          {item.duration} days
                        </Text>
                      </Card.Content>
                    </Card>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </FrostedSection>
          </Content>

          {/* DECORATIVE PURPLE BLOB BEHIND BUTTONS */}
          {/* Floating Buttons */}
          <TouchableOpacity
            onPress={() => router.push("/ai/ask")}
            style={{
              position: "absolute",
              bottom: 100,
              right: 20,
              backgroundColor: "#6C3BFF",
              padding: 18,
              borderRadius: 40,
              elevation: 5,
            }}
          >
            <MaterialIcons name="smart-toy" size={28} color="white" />
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => router.push("/createTrip")}
            style={{
              position: "absolute",
              bottom: 170,
              right: 20,
              backgroundColor: "#58C7FF",
              padding: 18,
              borderRadius: 40,
              elevation: 5,
            }}
          >
            <MaterialIcons name="add" size={28} color="white" />
          </TouchableOpacity>
        </LinearGradient>
      </ImageBackground>
      {/* ---------------- SIDEBAR / DRAWER ---------------- */}
<Modal
  visible={showSidebar}
  transparent
  animationType="slide"
  onRequestClose={() => setShowSidebar(false)}
>
  <TouchableOpacity
    activeOpacity={1}
    onPress={() => setShowSidebar(false)}
    style={{
      flex: 1,
      flexDirection: "row",
      backgroundColor: "rgba(0,0,0,0.4)",
    }}
  >
    {/* SIDEBAR PANEL */}
    <TouchableOpacity
      activeOpacity={1}
      style={{
        width: "75%",
        backgroundColor: "#ffffff",
        paddingTop: 60,
        paddingHorizontal: 20,
        elevation: 10,
      }}
    >
      {/* HEADER */}
      <Text
        style={{
          fontSize: 22,
          fontWeight: "800",
          marginBottom: 20,
        }}
      >
        Menu
      </Text>

      {/* ACTIVE TRIPS */}
      <TouchableOpacity
        onPress={() => {
          setShowSidebar(false);
          router.push("/traveleractivetrips");
        }}
        style={{
          flexDirection: "row",
          alignItems: "center",
          paddingVertical: 14,
        }}
      >
        <MaterialIcons
          name="tour"
          size={24}
          color="#6C3BFF"
          style={{ marginRight: 12 }}
        />
        <Text style={{ fontSize: 16, fontWeight: "600" }}>
          Active Trips
        </Text>
      </TouchableOpacity>

      {/* Divider */}
      <View
        style={{
          height: 1,
          backgroundColor: "#E5E7EB",
          marginVertical: 12,
        }}
      />
    </TouchableOpacity>
  </TouchableOpacity>
</Modal>
<Modal visible={reviewModalOpen} transparent animationType="slide">
  <View
    style={{
      flex: 1,
      backgroundColor: "rgba(0,0,0,0.5)",
      justifyContent: "center",
      alignItems: "center",
    }}
  >
    <View
      style={{
        width: "85%",
        backgroundColor: "white",
        borderRadius: 16,
        padding: 16,
      }}
    >
      <Text style={{ fontSize: 18, fontWeight: "800" }}>
        Leave a Review
      </Text>

      <Text style={{ marginTop: 10 }}>Rating: ⭐ {rating}</Text>

      {/* SIMPLE BUTTONS INSTEAD OF SLIDER (cleaner UX) */}
      <View style={{ flexDirection: "row", marginTop: 10 }}>
        {[1,2,3,4,5].map((r) => (
          <TouchableOpacity key={r} onPress={() => setRating(r)}>
            <Text style={{ fontSize: 24, marginHorizontal: 4 }}>
              {r <= rating ? "⭐" : "☆"}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <TextInput
        placeholder="Write your experience..."
        value={comment}
        onChangeText={setComment}
        multiline
        style={{
          borderWidth: 1,
          borderColor: "#ccc",
          borderRadius: 8,
          padding: 10,
          marginTop: 12,
        }}
      />

      <TouchableOpacity
        onPress={submitReview}
        disabled={submitting}
        style={{
          backgroundColor: "#6C3BFF",
          padding: 12,
          borderRadius: 10,
          marginTop: 14,
          alignItems: "center",
        }}
      >
        <Text style={{ color: "white", fontWeight: "700" }}>
          {submitting ? "Submitting..." : "Submit Review"}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity onPress={() => setReviewModalOpen(false)}>
        <Text style={{ marginTop: 10, textAlign: "center" }}>
          Cancel
        </Text>
      </TouchableOpacity>
    </View>
  </View>
</Modal>
    </ScreenWrapper>
  );
}