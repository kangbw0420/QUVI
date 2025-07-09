package com.daquv.agent.config;

import java.io.IOException;

import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletRequestWrapper;
import javax.servlet.http.HttpServletResponse;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.web.filter.OncePerRequestFilter;

@Configuration
public class UrlRewriteFilter extends OncePerRequestFilter {

    private static final Logger logger = LoggerFactory.getLogger(UrlRewriteFilter.class);

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {

        String requestURI = request.getRequestURI();
        logger.info("UrlRewriteFilter - Original URI: {}", requestURI);

        // //로 시작하는 URL을 /로 변환
        if (requestURI.startsWith("//")) {
            String newURI = "/" + requestURI.substring(2);
            logger.info("UrlRewriteFilter - Rewriting {} to {}", requestURI, newURI);

            HttpServletRequestWrapper wrappedRequest = new HttpServletRequestWrapper(request) {
                @Override
                public String getRequestURI() {
                    return newURI;
                }

                @Override
                public String getServletPath() {
                    return ""; // context-path가 /이므로 servletPath는 빈 문자열
                }

                @Override
                public String getPathInfo() {
                    return newURI; // 전체 경로를 pathInfo로 설정
                }
            };

            filterChain.doFilter(wrappedRequest, response);
        } else {
            logger.info("UrlRewriteFilter - No rewrite needed for: {}", requestURI);
            filterChain.doFilter(request, response);
        }
    }

    @Bean
    public FilterRegistrationBean<UrlRewriteFilter> urlRewriteFilterRegistration() {
        FilterRegistrationBean<UrlRewriteFilter> registration = new FilterRegistrationBean<>();
        registration.setFilter(this);
        registration.addUrlPatterns("/*");
        registration.setName("urlRewriteFilter");
        registration.setOrder(Ordered.HIGHEST_PRECEDENCE); // 가장 높은 우선순위
        return registration;
    }
}
