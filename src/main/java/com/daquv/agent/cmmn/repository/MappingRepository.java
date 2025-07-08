package com.daquv.agent.cmmn.repository;

import com.daquv.agent.cmmn.entity.TitleMapping;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MappingRepository extends JpaRepository<TitleMapping, Long> {
}
