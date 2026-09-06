//chat/[tripId].tsx
export const unstable_settings = { ssr: false };
import { CometChat } from "@cometchat/chat-sdk-react-native";
import { MaterialIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useLocalSearchParams } from "expo-router";
import React, { useEffect, useRef, useState } from "react";
import {
  FlatList,
  Image,
  KeyboardAvoidingView,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View
} from "react-native";
import { ActivityIndicator, Text } from "react-native-paper";

import { useRouter } from "expo-router";
import styled from "styled-components/native";
import { initCometChat } from "../../src/chat/cometchat";
import { api } from "../api/axiosInstance";

/* ---------------- TYPES ---------------- */

type MessageItem = {
  id: string;
  text: string;
  sender: string;
  mine: boolean;
  delivered?: boolean;
  read?: boolean;
};

const BackgroundPattern = styled.View`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
`;

console.log("🆕 Chat screen loaded");

export default function ChatScreen() {
  const { tripId } = useLocalSearchParams();
  const [darkMode, setDarkMode] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
const router = useRouter();
  const [peerUid, setPeerUid] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [chatLocked, setChatLocked] = useState(false);

  const [trip, setTrip] = useState<any>(null);
  const [showPostConfirmModal, setShowPostConfirmModal] = useState(false);
  const [isBroker, setIsBroker] = useState(false);

  const [showItinerary, setShowItinerary] = useState(false);
  const [itinerary, setItinerary] = useState<any>(null);
const [itinerarySource, setItinerarySource] = useState<"ai" | "broker" | null>(null);

  const loggedInUidRef = useRef<string | null>(null);

  // ✅ INTENT-EXPLICIT STATE
  const chatDisabled = trip?.status === "complete";
  const canConfirmTrip = !isBroker && trip?.status === "chatting";

  /* ---------------- INIT ---------------- */

  useEffect(() => {
    const setupChat = async () => {
      try {
        console.log("🟡 [Chat] Init started");

        await initCometChat();

        const token = await AsyncStorage.getItem("token");
        if (!token) throw new Error("JWT missing");

        console.log("🟡 [Chat] Fetching CometChat auth token");

        const authRes = await api.post(
          "/chat/token",
          {},
          { headers: { Authorization: `Bearer ${token}` } }
        );

        const { uid, authToken } = authRes.data;
        loggedInUidRef.current = uid;

        console.log("🟢 [Chat] Logging into CometChat");
        await CometChat.login(authToken);

        console.log("🟢 [Chat] Logged in as:", uid);

        const peerRes = await api.get(`/trips/${tripId}/chat-peer`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        setPeerUid(peerRes.data.peerUid);

        const tripRes = await api.get(`/trips/${tripId}/chat-context`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        setTrip(tripRes.data);

        // 🔥 AUTO-FETCH ITINERARY FOR BROKER (AI or Broker)
if (tripRes.data.broker_id === uid) {
  const itineraryRes = await api.get(
    `/trips/${tripId}/itinerary-context`,
    { headers: { Authorization: `Bearer ${token}` } }
  );

  setItinerary(itineraryRes.data.itinerary);
  setItinerarySource(itineraryRes.data.source); // "ai" | "broker"
  setShowItinerary(true); // auto popup
}

        // ✅ FIX: determine role of LOGGED-IN user
        if (tripRes.data.broker_id === uid) {
          setIsBroker(true);
        } else {
          setIsBroker(false);
        }

        setChatLocked(tripRes.data.status === "complete");

        /* 📜 Fetch previous messages */
        console.log("🟡 [Chat] Fetching message history");

        const req = new CometChat.MessagesRequestBuilder()
          .setUID(peerRes.data.peerUid)
          .setLimit(50)
          .build();

        const history = await req.fetchPrevious();

        setMessages(
          history.map((m: any) => ({
            id: String(m.getId()),
            text: m.getText(),
            sender: m.getSender().getUid(),
            mine: m.getSender().getUid() === uid,
            delivered: m.getDeliveredAt() > 0,
            read: m.getReadAt() > 0,
          }))
        );

        console.log("🟢 [Chat] Ready");
        setLoading(false);
      } catch (e) {
        console.error("🔴 Chat setup failed:", e);
        setError("Unable to open chat");
        setLoading(false);
      }
    };

    setupChat();
  }, []);

  /* ---------------- LISTENERS ---------------- */

  useEffect(() => {
    if (!peerUid || !loggedInUidRef.current) return;

    const listenerId = `trip_${tripId}`;

    CometChat.addMessageListener(
      listenerId,
      new CometChat.MessageListener({
        onTextMessageReceived: (msg: CometChat.TextMessage) => {
          setMessages((prev) => [
            ...prev,
            {
              id: String(msg.getId()),
              text: msg.getText(),
              sender: msg.getSender().getUid(),
              mine: msg.getSender().getUid() === loggedInUidRef.current,
            },
          ]);

          CometChat.markAsRead(msg);
        },

        onMessagesDelivered: (msg: CometChat.BaseMessage) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === String(msg.getId()) ? { ...m, delivered: true } : m
            )
          );
        },

        onMessagesRead: (msg: CometChat.BaseMessage) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === String(msg.getId()) ? { ...m, read: true } : m
            )
          );
        },

        onTypingStarted: () => setTyping(true),
        onTypingEnded: () => setTyping(false),
      })
    );

    return () => CometChat.removeMessageListener(listenerId);
  }, [peerUid]);

  /* ---------------- SEND ---------------- */

  const sendMessage = async () => {
    if (!input.trim() || !peerUid || chatDisabled) return;

    const msg = new CometChat.TextMessage(
      peerUid,
      input,
      CometChat.RECEIVER_TYPE.USER
    );

    const sent = await CometChat.sendMessage(msg);

    setMessages((prev) => [
      ...prev,
      {
        id: String(sent.getId()),
        text: input,
        sender: loggedInUidRef.current!,
        mine: true,
      },
    ]);

    setInput("");
  };

  /* ---------------- CONFIRM TRIP (TRAVELER ONLY) ---------------- */

 const confirmTrip = async () => {
  const token = await AsyncStorage.getItem("token");

  const res = await api.patch(
    `/trips/${tripId}/activate`,
    {},
    { headers: { Authorization: `Bearer ${token}` } }
  );

  setTrip(res.data.trip);

  // 👇 SHOW POST-CONFIRM POPUP
  setShowPostConfirmModal(true);
};

  /* ---------------- OPEN ITINERARY (BROKER ONLY) ---------------- */

  const openItinerary = () => {
    setShowItinerary(true);
  };

  /* ---------------- UI ---------------- */

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
        <Text>Opening chat…</Text>
      </View>
    );
  }

  if (error || !peerUid) {
    return (
      <View style={styles.center}>
        <Text style={{ color: "red" }}>{error}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
       {/* BACKGROUND */}
     <BackgroundPattern>
             <Image
               source={require("../../assets/images/pattern.jpg")}
               style={{ width: "100%", height: "100%" }}
               resizeMode="cover"
             />
           </BackgroundPattern>

           {/* NAVBAR - Floating Tilted Glass Effect */}
     <View
       style={{
         marginTop: 20, // space from very top
         marginHorizontal: 12,
         paddingVertical: 16,
         paddingHorizontal: 20,
     
         backgroundColor: darkMode
           ? "rgba(20,20,20,0.55)"
           : "rgba(255,255,255,0.55)",
     
         borderRadius: 18,
         borderTopLeftRadius: 28,
         borderBottomRightRadius: 28,
     
         transform: [{ rotate: "0deg" }], // ✨ Tilt effect
         backdropFilter: "blur(12px)", // iOS glass effect
     
         flexDirection: "row",
         justifyContent: "space-between",
         alignItems: "center",
     
         shadowColor: "#000",
         shadowOpacity: 0.15,
         shadowRadius: 12,
         shadowOffset: { width: 0, height: 4 },
         elevation: 8,
       }}
     >
       <View style={{ flexDirection: "row", alignItems: "center" }}>
        
         <Text
           style={{
             fontSize: 22,
             fontWeight: "bold",
             marginLeft: 10,
             
           }}
         >
           Trip Chat
         </Text>
       </View>
     
       {/* DARK MODE TOGGLE */}
       <TouchableOpacity onPress={() => setDarkMode(!darkMode)}>
         <Text style={{ fontSize: 26 }}>{darkMode ? "☀️" : "🌙"}</Text>
       </TouchableOpacity>
     </View>

      {/* 🧭 ITINERARY CARD (BROKER) */}
{trip && isBroker && (
  <TouchableOpacity
    style={styles.enhancedTripCard}
    activeOpacity={0.85}
    onPress={openItinerary}
  >
    {/* Header */}
    <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
      <Text style={styles.tripTitle}>{trip.destination}</Text>
      <Text style={styles.badge}>
        {itinerarySource === "ai" ? "AI" : "Broker"}
      </Text>
    </View>

    {/* Info */}
    <View style={{ marginTop: 6 }}>
      <Text style={styles.tripMeta}>💰 Budget: PKR {trip.budget}</Text>
      <Text style={styles.tripMeta}>
        📅 Status: {trip.status}
      </Text>
    </View>

    {/* CTA */}
    <View style={styles.ctaRow}>
      <Text style={styles.link}>View full itinerary</Text>
      <MaterialIcons name="arrow-forward-ios" size={16} color="#1D4ED8" />
    </View>
  </TouchableOpacity>
)}

     {/* CHAT */}
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <FlatList
          data={messages}
          keyExtractor={(item) => item.id}
          contentContainerStyle={{ padding: 16 }}
          renderItem={({ item }) => (
            <View
              style={[
                styles.bubble,
                item.mine ? styles.mine : styles.theirs,
              ]}
            >
              <Text>{item.text}</Text>
            </View>
          )}
        />
         {/* INPUT BAR */}
        {!chatDisabled && (
          <View style={styles.inputBar}>
            <TextInput
              value={input}
              onChangeText={setInput}
              placeholder="Type a message…"
              style={styles.input}
            />
            <TouchableOpacity onPress={sendMessage}>
              <MaterialIcons name="send" size={28} color="#6C3BFF" />
            </TouchableOpacity>
          </View>
        )}
      </KeyboardAvoidingView>

       {/* ✅ CONFIRM — TRAVELER ONLY, ONLY WHEN CHATTING */}
{canConfirmTrip && (
  <TouchableOpacity
    style={styles.confirmBtn}
    onPress={confirmTrip}
    disabled={trip?.status !== "chatting"}
  >
    <Text style={styles.confirmText}>
      Initiate Trip
    </Text>
  </TouchableOpacity>
)}

      
    {/* 🪟 ITINERARY MODAL */}
      <Modal visible={showItinerary} transparent animationType="fade">
  <View style={styles.overlay}>
    <View style={styles.modalCard}>

      {/* ❌ CLOSE ICON */}
      <TouchableOpacity
        style={styles.closeIcon}
        onPress={() => setShowItinerary(false)}
      >
        <MaterialIcons name="close" size={26} color="#000" />
      </TouchableOpacity>

      <ScrollView
        contentContainerStyle={{ paddingBottom: 20 }}
        showsVerticalScrollIndicator={false}
      >

        {/* TITLE */}
        <Text style={styles.modalTitle}>
          {itinerarySource === "ai"
            ? "AI Suggested Itinerary"
            : "Broker Itinerary"}
        </Text>

        <Text style={{ fontWeight: "600", marginBottom: 10 }}>
          {itinerary?.title || itinerary?.destination}
        </Text>

        {/* ================= AI ITINERARY ================= */}
        {itinerarySource === "ai" ? (
          <>
            <Text>Destination: {itinerary?.destination}</Text>
            <Text>Duration: {itinerary?.duration} days</Text>
            <Text>Budget: PKR {itinerary?.budget}</Text>

            {itinerary?.description && (
              <>
                <Text style={{ marginTop: 12, fontWeight: "700" }}>
                  Description
                </Text>
                <Text>{itinerary.description}</Text>
              </>
            )}

            {Array.isArray(itinerary?.itinerary_days) &&
              itinerary.itinerary_days.length > 0 && (
                <>
                  <Text
                    style={{
                      marginTop: 16,
                      fontWeight: "700",
                      fontSize: 16,
                    }}
                  >
                    Day-wise Plan
                  </Text>

                  {itinerary.itinerary_days.map(
                    (day: any, index: number) => (
                      <View key={index} style={{ marginTop: 12 }}>
                        <Text style={{ fontWeight: "600" }}>
                          {day.day}
                        </Text>

                        {Array.isArray(day.schedule) &&
                          day.schedule.map(
                            (item: any, i: number) => (
                              <Text
                                key={i}
                                style={{
                                  marginLeft: 10,
                                  marginTop: 4,
                                }}
                              >
                                • {item.time} — {item.activity}
                              </Text>
                            )
                          )}
                      </View>
                    )
                  )}
                </>
              )}
          </>
        ) : (
          /* ================= BROKER ITINERARY ================= */
          <>
            <Text>Destination: {itinerary?.arrival_location}</Text>
            <Text>Duration: {itinerary?.duration_days} days</Text>
            <Text>Price: PKR {itinerary?.price_per_person}</Text>

            {itinerary?.description && (
              <>
                <Text style={{ marginTop: 12, fontWeight: "700" }}>
                  Description
                </Text>
                <Text>{itinerary.description}</Text>
              </>
            )}

            {Array.isArray(itinerary?.days) &&
              itinerary.days.length > 0 && (
                <>
                  <Text
                    style={{
                      marginTop: 16,
                      fontWeight: "700",
                      fontSize: 16,
                    }}
                  >
                    Day-wise Plan
                  </Text>

                  {itinerary.days.map((day: any, index: number) => (
                    <View key={index} style={{ marginTop: 12 }}>
                      <Text style={{ fontWeight: "600" }}>
                        Day {day.day_number}
                      </Text>

                      {Array.isArray(day.activities) &&
                        day.activities.map(
                          (activity: string, i: number) => (
                            <Text
                              key={i}
                              style={{
                                marginLeft: 10,
                                marginTop: 4,
                              }}
                            >
                              • {activity}
                            </Text>
                          )
                        )}
                    </View>
                  ))}
                </>
              )}
          </>
        )}
      </ScrollView>
    </View>
  </View>
</Modal>
      {/* ✅ POST-CONFIRM ACTION MODAL */}
<Modal
  visible={showPostConfirmModal}
  transparent
  animationType="fade"
>
  <View style={styles.overlay}>
    <View style={[styles.modalCard, { height: "auto" }]}>
      <Text style={styles.modalTitle}>
        Trip Activated 🎉
      </Text>

      <Text style={{ marginBottom: 16, color: "#374151" }}>
        Your trip is now active. What would you like to do next?
      </Text>

      {/* Continue Chatting */}
      <TouchableOpacity
        style={[styles.confirmBtn, { marginBottom: 10 }]}
        onPress={() => setShowPostConfirmModal(false)}
      >
        <Text style={styles.confirmText}>
          Continue Chatting
        </Text>
      </TouchableOpacity>

      {/* Go to Active Trips */}
      <TouchableOpacity
        style={[
          styles.confirmBtn,
          { backgroundColor: "#2563EB" },
        ]}
        onPress={() => {
          setShowPostConfirmModal(false);
          // 👇 navigate to active trips screen
          // adjust route if your path differs
          router.replace("/traveleractivetrips");
        }}
      >
        <Text style={styles.confirmText}>
          View Active Trips
        </Text>
      </TouchableOpacity>
    </View>
  </View>
</Modal>

    </View>
  );
}

/* ---------------- STYLES ---------------- */

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },

  navbar: {
    height: 56,
    backgroundColor: "#2563EB",
    justifyContent: "center",
    paddingHorizontal: 16,
  },
   inputBar: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    margin: 10,
    paddingHorizontal: 14,
    borderRadius: 30,
    elevation: 8,
    bottom:20,
  },
  navTitle: { color: "#fff", fontSize: 18, fontWeight: "700" },

  tripCard: {
    padding: 12,
    backgroundColor: "#E0E7FF",
    borderBottomWidth: 1,
    borderColor: "#C7D2FE",
  },
  glassNavbar: {
    marginTop: 20,
    marginHorizontal: 12,
    padding: 16,
    borderRadius: 18,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    elevation: 8,
  },
  closeIcon: {
    position: "absolute",
    right: 12,
    top: 12,
    zIndex: 10,
  },
  tripTitle: { fontSize: 16, fontWeight: "700" },
  link: { color: "#1D4ED8", marginTop: 4 },

  bubble: {
    padding: 12,
    borderRadius: 14,
    marginVertical: 6,
    maxWidth: "75%",
  },
  mine: {
    backgroundColor: "#f6f6f78e",
    alignSelf: "flex-end",
  },
  theirs: {
    backgroundColor: "#FFE7C7",
    alignSelf: "flex-start",
  },

  receipt: { fontSize: 10, color: "#6B7280", marginTop: 4 },

  composer: {
    flexDirection: "row",
    padding: 8,
    borderTopWidth: 1,
    borderColor: "#E5E7EB",
    backgroundColor: "#fff",
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#D1D5DB",
    borderRadius: 6,
    paddingHorizontal: 8,
    
  },
  send: { marginLeft: 12, color: "#2563EB", fontWeight: "700", bottom:20, },

  typing: { marginLeft: 10, color: "#6B7280", fontSize: 12 },

  confirmBtn: {
    margin: 8,
    padding: 12,
    backgroundColor: "#1ec2dfff",
    borderRadius: 8,
    alignItems: "center",
    bottom: 20,
  },
  confirmText: { color: "#fff", fontWeight: "700" },

  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalCard: {
    width: "90%",
    height: "35%",
    backgroundColor: "#ffffffff",
    borderRadius: 12,
    padding: 16,
  },
  modalTitle: { fontSize: 18, fontWeight: "700", marginBottom: 8 },
  closeBtn: {
    marginTop: 12,
    backgroundColor: "#2563EB",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
  },

  enhancedTripCard: {
  marginHorizontal: 12,
  marginTop: 12,
  padding: 14,
  borderRadius: 14,
  backgroundColor: "rgba(255,255,255,0.75)",
  borderWidth: 1,
  borderColor: "#E0E7FF",

  shadowColor: "#000",
  shadowOpacity: 0.1,
  shadowRadius: 8,
  shadowOffset: { width: 0, height: 3 },
  elevation: 6,
},

tripMeta: {
  fontSize: 13,
  color: "#374151",
},

badge: {
  backgroundColor: "#E0E7FF",
  color: "#3730A3",
  paddingHorizontal: 8,
  paddingVertical: 2,
  borderRadius: 8,
  fontSize: 12,
  fontWeight: "700",
},

ctaRow: {
  marginTop: 10,
  flexDirection: "row",
  alignItems: "center",
  justifyContent: "space-between",
},
});