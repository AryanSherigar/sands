CREATE SEQUENCE simulation_commands_acceptance_sequence AS bigint;

ALTER TABLE simulation_commands ADD COLUMN acceptance_sequence bigint;

WITH acceptance_order AS (
    SELECT command.playthrough_id, command.command_id,
           row_number() OVER (
               ORDER BY command.accepted_turn, command.accepted_wave,
                        COALESCE(operation.result_version, 0),
                        command.playthrough_id, command.actor_id, command.command_id
           ) AS position
    FROM simulation_commands AS command
    LEFT JOIN simulation_operations AS operation
      ON operation.playthrough_id = command.playthrough_id
     AND operation.actor_id = command.actor_id
     AND operation.operation_id = command.operation_id
)
UPDATE simulation_commands AS command
SET acceptance_sequence = acceptance_order.position
FROM acceptance_order
WHERE command.playthrough_id = acceptance_order.playthrough_id
  AND command.command_id = acceptance_order.command_id;

SELECT setval('simulation_commands_acceptance_sequence',
              COALESCE((SELECT max(acceptance_sequence) FROM simulation_commands), 0) + 1,
              false);

ALTER TABLE simulation_commands
    ALTER COLUMN acceptance_sequence SET DEFAULT nextval('simulation_commands_acceptance_sequence'),
    ALTER COLUMN acceptance_sequence SET NOT NULL,
    ADD CONSTRAINT simulation_commands_acceptance_positive CHECK (acceptance_sequence > 0);

ALTER SEQUENCE simulation_commands_acceptance_sequence
    OWNED BY simulation_commands.acceptance_sequence;

CREATE UNIQUE INDEX simulation_commands_acceptance_idx
    ON simulation_commands (playthrough_id, actor_id, acceptance_sequence);
