package com.daquv.agent.quvi.repository;

import com.daquv.agent.quvi.entity.Users;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface UsersRepository extends JpaRepository<Users, Long> {
    @Query("SELECT u.companyId FROM Users u WHERE u.userId = :userId")
    Optional<String> findCompanyIdByUserId(@Param("userId") String userId);
}
