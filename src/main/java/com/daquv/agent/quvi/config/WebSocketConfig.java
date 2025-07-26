package com.daquv.agent.quvi.config;

import com.daquv.agent.quvi.ChatWebSocketHandler;
import com.daquv.agent.quvi.ResumeWebSocketHandler;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * WebSocket 설정
 * Chat과 HIL 재개를 위한 WebSocket 엔드포인트 설정
 */
@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    @Autowired
    private ChatWebSocketHandler chatWebSocketHandler;

    @Autowired
    private ResumeWebSocketHandler resumeWebSocketHandler;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        // Chat WebSocket 엔드포인트 등록
        registry.addHandler(chatWebSocketHandler, "/ws/chat")
                .setAllowedOriginPatterns("*"); // CORS 설정
        
        // HIL 재개 WebSocket 엔드포인트 등록
        registry.addHandler(resumeWebSocketHandler, "/ws/resume")
                .setAllowedOriginPatterns("*"); // CORS 설정
    }
} 