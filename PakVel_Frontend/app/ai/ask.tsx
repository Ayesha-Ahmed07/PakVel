import { MaterialIcons } from "@expo/vector-icons";
import React, { useRef, useState } from "react";
import {
  Animated,
  Image,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  TouchableOpacity,
  View
} from "react-native";
import { Chip, TextInput } from "react-native-paper";
import styled from "styled-components/native";
import { api } from "../api/axiosInstance";

/* ----------------------------------
   🎨 LIGHT & DARK THEMES
---------------------------------- */
const lightTheme = {
  background: "#ffffff00",
  navbar: "#ffffff",
  navbarText: "#000",
  botBubble: "#FFE7C7",
  userBubble: "#6C3BFF",
  textUser: "#fff",
  textBot: "#333",
  inputBg: "#ffffff",
  modalBg: "#ffffff",
  avatarBotBg: "#6C3BFF",
  avatarUserBg: "#2DD4BF",
};

const darkTheme = {
  background: "#00000099",
  navbar: "#1a1a1a",
  navbarText: "#fff",
  botBubble: "#2d2d2d",
  userBubble: "#7b5bff",
  textUser: "#fff",
  textBot: "#e6e6e6",
  inputBg: "#1c1c1c",
  modalBg: "#1e1e1e",
  avatarBotBg: "#7b5bff",
  avatarUserBg: "#14b8a6",
};

/* ----------------------------------
   🎨 Styled Components
---------------------------------- */
const Screen = styled.View`
  flex: 1;
`;

const BackgroundPattern = styled.View`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
`;

const ChatContainer = styled(ScrollView)`
  padding: 20px;
`;

const Row = styled.View`
  flex-direction: row;
  align-items: flex-end;
`;

const Avatar = styled(Animated.View)`
  width: 36px;
  height: 36px;
  border-radius: 18px;
  margin-right: 10px;
  overflow: hidden;
`;

const BubbleBase = styled(Animated.View)`
  padding: 14px;
  margin-vertical: 6px;
  max-width: 78%;
  border-radius: 18px;
  elevation: 4;
`;

const Text = styled.Text``;

const InputBar = styled.View`
  flex-direction: row;
  align-items: center;
  padding: 10px;
  border-radius: 30px;
  elevation: 10;
  margin: 10px;
`;

/* ----------------------------------
        MAIN COMPONENT
---------------------------------- */
export default function AskAI() {
  const [darkMode, setDarkMode] = useState(false);
  const theme = darkMode ? darkTheme : lightTheme;

  const [messages, setMessages] = useState<
    { text: string; isUser: boolean }[]
  >([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const scrollRef = useRef<any>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  /* Suggestion Chips (STATIC, shown above input bar) */
  const suggestions = [
    "Famous places in Islamabad",
    "Modify my itinerary",
    "Best time to visit Skardu",
  ];

  /* ----------------------------------
      Animations
  ---------------------------------- */
  const animateBubble = () => {
    fadeAnim.setValue(0);
    Animated.spring(fadeAnim, {
      toValue: 1,
      friction: 5,
      tension: 90,
      useNativeDriver: true,
    }).start();
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollRef.current?.scrollToEnd({ animated: true });
    }, 150);
  };

  /* ----------------------------------
      SEND MESSAGE
  ---------------------------------- */
  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { text: input, isUser: true };
    setMessages((prev) => [...prev, userMsg]);
    animateBubble();
    scrollToBottom();
    setInput("");
    setLoading(true);

    try {
      const res = await api.post("/traveler/chat", {
        message: userMsg.text,
      });

      const botReply = {
        text: res.data.reply,
        isUser: false,
      };

      setMessages((prev) => [...prev, botReply]);
      animateBubble();
      scrollToBottom();
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { text: "AI service unavailable.", isUser: false },
      ]);
    }

    setLoading(false);
  };

  /* ----------------------------------
      Avatars
  ---------------------------------- */
  const BotAvatar = () => (
    <Avatar>
      <View
        style={{
          backgroundColor: theme.avatarBotBg,
          width: "100%",
          height: "100%",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Text style={{ color: "white", fontSize: 22 }}>🤖</Text>
      </View>
    </Avatar>
  );

  const UserAvatar = () => (
    <Avatar>
      <View
        style={{
          backgroundColor: theme.avatarUserBg,
          width: "100%",
          height: "100%",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Text style={{ color: "white", fontSize: 22 }}>🧍</Text>
      </View>
    </Avatar>
  );

  /* ----------------------------------
        UI + Render
  ---------------------------------- */
  return (
    <Screen>
      {/* Background Image */}
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
    <Text style={{ fontSize: 26 }}>🧭</Text>
    <Text
      style={{
        fontSize: 22,
        fontWeight: "bold",
        marginLeft: 10,
        color: theme.navbarText,
      }}
    >
      Pakvel AI
    </Text>
  </View>

  {/* DARK MODE TOGGLE */}
  <TouchableOpacity onPress={() => setDarkMode(!darkMode)}>
    <Text style={{ fontSize: 26 }}>{darkMode ? "☀️" : "🌙"}</Text>
  </TouchableOpacity>
</View>
      {/* Chat Area */}
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ChatContainer ref={scrollRef}>
          {messages.map((msg, index) => {
            const bubbleColor = msg.isUser
              ? theme.userBubble
              : theme.botBubble;

            const textColor = msg.isUser
              ? theme.textUser
              : theme.textBot;

            return (
              <Row
                key={index}
                style={{
                  justifyContent: msg.isUser ? "flex-end" : "flex-start",
                }}
              >
                {!msg.isUser && <BotAvatar />}

                <BubbleBase
                  style={{
                    backgroundColor: bubbleColor,
                    opacity: fadeAnim,
                  }}
                >
                  <Text style={{ color: textColor }}>{msg.text}</Text>
                </BubbleBase>

                {msg.isUser && <UserAvatar />}
              </Row>
            );
          })}

          {/* Typing Indicator */}
          {loading && (
            <Row style={{ marginTop: 10 }}>
              <BotAvatar />
              <BubbleBase
                style={{
                  backgroundColor: theme.botBubble,
                  paddingVertical: 10,
                  paddingHorizontal: 16,
                }}
              >
                <Text style={{ fontSize: 18 }}>● ● ●</Text>
              </BubbleBase>
            </Row>
          )}
        </ChatContainer>

        {/* ----------------------------------
            USER SUGGESTIONS (always visible)
        ---------------------------------- */}
        <View
          style={{
            flexDirection: "row",
            flexWrap: "wrap",
            paddingHorizontal: 20,
            marginBottom: 4,
          }}
        >
          {suggestions.map((s, i) => (
            <Chip
              key={i}
              style={{
                marginRight: 8,
                marginBottom: 6,
                backgroundColor: "#FFF",
                borderColor: "#6C3BFF",
              }}
              onPress={() => setInput(s)}
            >
              {s}
            </Chip>
          ))}
        </View>

        {/* Input Bar */}
        <InputBar style={{ backgroundColor: theme.inputBg }}>
          <TextInput
            value={input}
            onChangeText={setInput}
            placeholder="Ask Pakvel AI…"
            placeholderTextColor={darkMode ? "#aaa" : "#666"}
            style={{
              flex: 1,
              backgroundColor: "transparent",
              color: darkMode ? "#fff" : "#000",
            }}
            mode="flat"
            underlineColor="transparent"
            activeUnderlineColor="transparent"
          />

          <TouchableOpacity onPress={sendMessage}>
            <MaterialIcons
              name="send"
              size={30}
              color={darkMode ? "#9F7BFF" : "#6C3BFF"}
              style={{ marginLeft: 10 }}
            />
          </TouchableOpacity>
        </InputBar>
      </KeyboardAvoidingView>
    </Screen>
  );
}