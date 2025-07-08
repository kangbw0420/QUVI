package com.daquv.agent.quvi.config;

import com.daquv.agent.quvi.QuviWebSocketHandler;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * WebSocket 설정
 * 일반 WebSocket을 사용하여 /process 엔드포인트 처리
 */
@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    @Autowired
    private QuviWebSocketHandler quviWebSocketHandler;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        // WebSocket 엔드포인트 등록 - /ws/process로 변경
        registry.addHandler(quviWebSocketHandler, "/ws/process")
                .setAllowedOriginPatterns("*"); // CORS 설정
    }
} 