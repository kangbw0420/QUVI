{% macro render_simple_case(column, category, alias_name) %}
  {% set my_yaml = var('my_yaml') %}
  {% set table = my_yaml %}
  
    CASE
      {% for label, values in table[category].items() if label != 'default' %}
        WHEN {{ column }} IN (
          {% for v in values %}
            '{{ v }}'{% if not loop.last %}, {% endif %}
          {% endfor %}
        ) THEN '{{ label }}'
      {% endfor %}
      ELSE '{{ table[category]['default'] }}'
    END
   AS {{ alias_name }},
{% endmacro %}
