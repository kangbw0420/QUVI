package com.daquv.agent.cmmn.repository;

import com.daquv.agent.cmmn.entity.Users;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface AuthRepository extends JpaRepository<Users, Long> {
    Optional<Users> findByUserId(String userId);
}
