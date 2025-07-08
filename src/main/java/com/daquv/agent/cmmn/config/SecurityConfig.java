package com.daquv.agent.cmmn.config;

import com.daquv.agent.cmmn.util.JwtAuthenticationFilter;
import com.daquv.agent.cmmn.util.PythonCompatiblePasswordEncoder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configuration.WebSecurityConfigurerAdapter;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.web.firewall.HttpFirewall;
import org.springframework.security.web.firewall.StrictHttpFirewall;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;

@Configuration
@EnableWebSecurity
public class SecurityConfig extends WebSecurityConfigurerAdapter {

    @Autowired
    private JwtAuthenticationFilter jwtAuthenticationFilter;

    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http
                .cors().and()
                .csrf().disable()
                .sessionManagement().sessionCreationPolicy(SessionCreationPolicy.STATELESS)
                .and()
                .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class)
                .headers()
                .frameOptions().deny()                    // X-Frame-Options 헤더 설정
                .xssProtection().and()                    // XSS 보호
                .contentTypeOptions().and()               // Content-Type 스니핑 방지
                .and()
                .authorizeRequests()
                // 인증이 필요 없는 공개 엔드포인트
                .antMatchers("/login").permitAll()           // 인증 관련 (로그인, 논스 등)
                .antMatchers("/health").permitAll()
                .antMatchers("/process").permitAll()         // process 엔드포인트는 인증 없이 허용

                // 인증이 필요한 엔드포인트
                .antMatchers("/save_history").authenticated()
                .antMatchers("/history").authenticated()
                .antMatchers("/recommend").authenticated()
                .antMatchers("/users/me").authenticated()

                // 특정 엔드포인트만 예외 처리하는 경우
                .antMatchers("/mapping/getAll").permitAll()    // 매핑 조회는 인증 없이 허용
                .antMatchers("/mapping/**").authenticated()    // 나머지 매핑 API는 인증 필요

                // 기타 모든 요청은 인증 필요
                .anyRequest().authenticated()
                .and()
                .exceptionHandling()
                .authenticationEntryPoint((request, response, authException) -> {
                    response.setStatus(401);
                    response.setContentType("application/json");
                    response.getWriter().write("{\"error\":\"인증이 필요합니다.\"}");
                })
                .accessDeniedHandler((request, response, accessDeniedException) -> {
                    response.setStatus(403);
                    response.setContentType("application/json");
                    response.getWriter().write("{\"error\":\"접근 권한이 없습니다.\"}");
                });
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new PythonCompatiblePasswordEncoder();
    }

    @Bean
    public HttpFirewall allowUrlEncodedSlashHttpFirewall() {
        StrictHttpFirewall firewall = new StrictHttpFirewall();
        firewall.setAllowUrlEncodedSlash(true);
        firewall.setAllowSemicolon(true);
        firewall.setAllowBackSlash(true);
        firewall.setAllowUrlEncodedDoubleSlash(true);
        return firewall;
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOriginPatterns(Arrays.asList("*"));
        configuration.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(Arrays.asList("*"));
        configuration.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }
}