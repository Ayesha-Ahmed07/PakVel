import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { LinearGradient } from "expo-linear-gradient";
import { useLocalSearchParams, useRouter } from "expo-router";
import React, { useEffect, useState } from "react";
import {
  Dimensions,
  FlatList,
  ImageBackground,
  Linking,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  View,
} from "react-native";
import { ActivityIndicator, Card, Text } from "react-native-paper";
import { api } from "../api/axiosInstance";

// Ensure full-height background on all screens
const SCREEN_HEIGHT = Dimensions.get("window").height;

const cityImages: Record<string, any> = {
  islamabad: require("../../assets/images/islamabad.jpg"),
  hyderabad: require("../../assets/images/hyderabad.png"),
  quetta: require("../../assets/images/Quetta.png"),
  karachi: require("../../assets/images/karachi.jpg"),
  lahore: require("../../assets/images/lahore.jpg"),
  faislabad: require("../../assets/images/faislabad.jpg"),
  chitral: require("../../assets/images/chitral.jpg"),
  hunza: require("../../assets/images/hunza.jpg"),
  kashmir: require("../../assets/images/kashmir.png"),
  malamjabba: require("../../assets/images/malamjabba.jpg"),
};

const getCityImage = (city: string) => {
  const key = city?.trim().toLowerCase();
  return cityImages[key] || require("../../assets/images/background.jpg");
};

const getIcon = (text: string) => {
  if (text.toLowerCase().includes("breakfast")) return "🍳";
  if (text.toLowerCase().includes("lunch")) return "🍽️";
  if (text.toLowerCase().includes("dinner")) return "🍽️";
  if (text.toLowerCase().includes("hotel")) return "🏨";
  if (text.toLowerCase().includes("visit")) return "📍";
  return "✨";
};

export default function ItineraryScreen() {
  const { id } = useLocalSearchParams();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [itinerary, setItinerary] = useState<any>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    try {
      const token = await AsyncStorage.getItem("token");
      const res = await api.get(`/traveler/itinerary/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      setItinerary(res.data);
    } catch (err) {
      console.log("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  // Loading Screen
  if (loading || !itinerary) {
    return (
      <LinearGradient colors={["#F0F7FF", "#E8EBFF"]} style={{ flex: 1 }}>
        <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
          <ActivityIndicator size="large" />
          <Text>Loading itinerary...</Text>
        </View>
      </LinearGradient>
    );
  }

  return (
    <ImageBackground
      source={getCityImage(itinerary.destination)}
      style={{
        flex: 1,
        width: "100%",
        height: SCREEN_HEIGHT,   // 🟦 Full device height (fixes crop)
      }}
      resizeMode="cover"
      imageStyle={{
        opacity: 0.80,            // 🟦 Perfect clarity — not too faded
      }}
    >
      {/* Soft overlay gradient so text stays readable */}
      <LinearGradient
        colors={[
          "rgba(0,0,0,0.10)",
          "rgba(0,0,0,0.20)",
          "rgba(0,0,0,0.25)",
        ]}
        style={{
          flex: 1,
          width: "100%",
          height: "100%",
          paddingTop: 20,
        }}
      >

        {/* Back Button */}
        <TouchableOpacity
          onPress={() => router.back()}
          style={{
            position: "absolute",
            top: 50,
            left: 20,
            zIndex: 10,
            backgroundColor: "rgba(108,59,255,0.9)",
            padding: 12,
            borderRadius: 40,
          }}
        >
          <MaterialIcons name="arrow-back" size={26} color="white" />
        </TouchableOpacity>

        {/* Main Content */}
        <ScrollView
          contentContainerStyle={{
            padding: 20,
            paddingTop: 100,
            paddingBottom: 60,
          }}
        >
         
         <View style={{ marginBottom: 20 }}>
  <Text style={{
    fontSize: 34,
    fontWeight: "900",
    color: "#0c0804ff",
    textAlign: "center"
  }}>
    {itinerary.destination}
  </Text>

  <Text style={{
  textAlign: "center",
  color: "#0c0804ff",
  marginTop: 6
}}>
  • 
  {itinerary.duration} Days •{" "}
  {itinerary.budget === "low" && "💵 Low Budget"}
  {itinerary.budget === "moderate" && "💳 Moderate Budget"}
  {itinerary.budget === "high" && "💎 Premium Budget"}
</Text>
</View>



          {/* Daily Schedule Cards */}
          <FlatList
  data={itinerary.itinerary_days}
  horizontal
  pagingEnabled
  showsHorizontalScrollIndicator={false}
  keyExtractor={(_, index) => index.toString()}
  onMomentumScrollEnd={(event) => {
    const index = Math.round(
      event.nativeEvent.contentOffset.x /
      (Dimensions.get("window").width - 40)
    );
    setActiveIndex(index);
  }}
  renderItem={({ item: day, index }) => (
    <View
      style={{
        width: Dimensions.get("window").width - 40,
        marginRight: 20,
      }}
    >
      <Card
        style={{
          padding: 20,
          borderRadius: 18,
          backgroundColor: "rgba(255,255,255,0.75)",
          borderWidth: 1,
          borderColor: "rgba(255,255,255,0.3)"
        }}
      >
        <Text style={{ fontSize: 20, fontWeight: "800", marginBottom: 10 }}>
          {day.day}
        </Text>

        {day.schedule.map((item: any, idx: number) => (
          <View
            key={idx}
            style={{ flexDirection: "row", marginBottom: 16 }}
          >
            {/* TIMELINE */}
            <View style={{ alignItems: "center", marginRight: 12 }}>
              <View
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 5,
                  backgroundColor: "#6C3BFF",
                }}
              />
              {idx !== day.schedule.length - 1 && (
                <View
                  style={{
                    width: 2,
                    flex: 1,
                    backgroundColor: "#131417ff",
                  }}
                />
              )}
            </View>

            {/* CONTENT */}
            <View style={{ flex: 1 }}>
              <Text style={{ fontWeight: "900", color: "#333" }}>
                {item.time}
              </Text>

              {/* ACTIVITY TEXT (CLICKABLE) */}
<Text
  style={{ marginTop: 4, color: "#444", textDecorationLine: item.link ? "underline" : "none" }}
  onPress={() => item.link && Linking.openURL(item.link)}
>
  {getIcon(item.activity)} {item.activity}
</Text>

{/* TYPE (LOW / MODERATE / HIGH) */}
{item.type && (
  <Text style={{ fontSize: 12, color: "#888", marginTop: 3 }}>
    💰 {item.type.toUpperCase()}
  </Text>
)}
            </View>
          </View>
        ))}
      </Card>
    </View>
  )}
/>
<View style={{ flexDirection: "row", justifyContent: "center", marginTop: 10 }}>
  {itinerary.itinerary_days.map((_: any, i: number) => (
    <View
      key={i}
      style={{
        width: activeIndex === i ? 12 : 8,
        height: activeIndex === i ? 12 : 8,
        borderRadius: 6,
        backgroundColor: "white",
        margin: 4,
        opacity: activeIndex === i ? 1 : 0.3,
      }}
    />
  ))}
</View>
        </ScrollView>

        {/* ACTION BUTTONS */}
{/* PREMIUM ACTION SECTION */}
<View style={styles.actionWrapper}>

  <View style={styles.segmentContainer}>

    {/* SELF BOOK (PRIMARY) */}
    <TouchableOpacity
      style={styles.primarySegment}
      activeOpacity={0.85}
      onPress={async () => {
        const token = await AsyncStorage.getItem("token");

        const res = await api.post(
          "/trips/",
          {
            itinerary_id: id,   // ✅ fixed key
            trip_type: "ai_self",
            destination: itinerary.destination,
            budget: itinerary.budget,
          },
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        router.push({
          pathname: "/selfbook",
          params: { 
            tripId: res.data.trip_id,
            itineraryId: id

           },
        });
      }}
    >
      <LinearGradient
        colors={["#5B5FFF", "#8E54E9"]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.gradientBtn}
      >
        <MaterialIcons name="flight-takeoff" size={18} color="white" />
        <Text style={styles.primaryText}>Self Book</Text>
      </LinearGradient>
    </TouchableOpacity>

    {/* BROKER MARKETPLACE (SECONDARY) */}
    <TouchableOpacity
      style={styles.secondarySegment}
      activeOpacity={0.85}
      onPress={() =>
        router.push({
          pathname: "/brokerMarketplace",
          params: {
            itineraryId: id,
            destination: itinerary.destination,
            budget: itinerary.budget
          },
        })
      }
    >
      <MaterialIcons name="storefront" size={18} color="#6C3BFF" />
      <Text style={styles.secondaryText}>
        Broker Marketplace
      </Text>
    </TouchableOpacity>

  </View>

</View>
      </LinearGradient>
    </ImageBackground>
  );
}


const styles = StyleSheet.create({
actionWrapper: {
  paddingHorizontal: 20,
  paddingBottom: 30,
},

segmentContainer: {
  flexDirection: "row",
  backgroundColor: "rgba(255,255,255,0.9)",
  borderRadius: 30,
  padding: 6,
  elevation: 6,
  shadowColor: "#000",
  shadowOpacity: 0.1,
  shadowRadius: 8,
  shadowOffset: { width: 0, height: 4 },
  bottom:20,
},

primarySegment: {
  flex: 1,
  borderRadius: 30,
  overflow: "hidden",
},

gradientBtn: {
  flexDirection: "row",
  justifyContent: "center",
  alignItems: "center",
  paddingVertical: 14,
  borderRadius: 30,
},

primaryText: {
  color: "white",
  fontWeight: "700",
  marginLeft: 8,
},

secondarySegment: {
  flex: 1,
  borderRadius: 30,
  flexDirection: "row",
  justifyContent: "center",
  alignItems: "center",
  paddingVertical: 14,
  borderWidth: 1.5,
  borderColor: "#6C3BFF",
  backgroundColor: "white",
},

secondaryText: {
  color: "#6C3BFF",
  fontWeight: "700",
  marginLeft: 8,
},
});