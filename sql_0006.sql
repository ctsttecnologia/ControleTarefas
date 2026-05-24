--
-- Add field data_necessaria to pedido
--
ALTER TABLE `suprimentos_pedido` ADD COLUMN `data_necessaria` date NULL;
--
-- Add field descricao_material to pedido
--
ALTER TABLE `suprimentos_pedido` ADD COLUMN `descricao_material` longtext DEFAULT ('') NOT NULL;
--
-- Add field motivo_revisao to pedido
--
ALTER TABLE `suprimentos_pedido` ADD COLUMN `motivo_revisao` longtext DEFAULT ('') NOT NULL;
--
-- Add field quantidade to pedido
--
ALTER TABLE `suprimentos_pedido` ADD COLUMN `quantidade` numeric(12, 2) NULL;
--
-- Add field tipo_insumo to pedido
--
ALTER TABLE `suprimentos_pedido` ADD COLUMN `tipo_insumo` varchar(30) DEFAULT '' NOT NULL;
ALTER TABLE `suprimentos_pedido` ALTER COLUMN `tipo_insumo` DROP DEFAULT;
--
-- Add field tipo_obra to pedido
--
ALTER TABLE `suprimentos_pedido` ADD COLUMN `tipo_obra` varchar(2) DEFAULT 'CM' NOT NULL;
ALTER TABLE `suprimentos_pedido` ALTER COLUMN `tipo_obra` DROP DEFAULT;
--
-- Add field unidade_medida to pedido
--
ALTER TABLE `suprimentos_pedido` ADD COLUMN `unidade_medida` varchar(20) DEFAULT 'UNID' NOT NULL;
ALTER TABLE `suprimentos_pedido` ALTER COLUMN `unidade_medida` DROP DEFAULT;
--
-- Alter field custo_real on itempedido
--
-- (no-op)
--
-- Alter field aprovador on pedido
--
-- (no-op)
--
-- Alter field estoque_processado on pedido
--
-- (no-op)
--
-- Alter field status on pedido
--
-- (no-op)
--
-- Create model SolicitacaoCompra
--
CREATE TABLE `suprimentos_solicitacaocompra` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `numero` varchar(30) NOT NULL UNIQUE, `status` varchar(25) NOT NULL, `tipo_obra` varchar(2) NOT NULL, `descricao_material` longtext NOT NULL, `quantidade` numeric(12, 2) NULL, `unidade_medida` varchar(20) NOT NULL, `tipo_insumo` varchar(30) NOT NULL, `data_necessaria` date NULL, `data_aprovacao_inicial` datetime(6) NULL, `data_cotacao` date NULL, `numero_cotacao` varchar(50) NOT NULL, `cnpj_compra` varchar(18) NOT NULL, `tipo_nota_fiscal` varchar(20) NOT NULL, `data_validacao_cotacao` date NULL, `data_criacao_pedido` date NULL, `numero_pedido_sienge` varchar(50) NOT NULL, `valor_pedido` numeric(14, 2) NULL, `data_aprovacao_pedido` date NULL, `data_envio_fornecedor` date NULL, `data_prevista_entrega` date NULL, `data_entrega_efetiva` date NULL, `numero_nota_fiscal` varchar(50) NOT NULL, `observacoes` longtext NOT NULL, `motivo_cancelamento` longtext NOT NULL, `criado_em` datetime(6) NOT NULL, `atualizado_em` datetime(6) NOT NULL, `aprovador_cotacao_id` bigint NULL, `aprovador_inicial_id` bigint NULL, `aprovador_pedido_id` bigint NULL, `comprador_id` bigint NULL, `contrato_id` bigint NOT NULL, `filial_id` bigint NULL, `fornecedor_id` bigint NULL, `solicitante_id` bigint NOT NULL);
--
-- Create model HistoricoSolicitacao
--
CREATE TABLE `suprimentos_historicosolicitacao` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `versao` integer UNSIGNED NOT NULL CHECK (`versao` >= 0), `descricao` longtext NOT NULL, `status_anterior` varchar(25) NOT NULL, `status_novo` varchar(25) NOT NULL, `criado_em` datetime(6) NOT NULL, `responsavel_id` bigint NULL, `solicitacao_id` bigint NOT NULL);
--
-- Create model HistoricoPedido
--
CREATE TABLE `suprimentos_historicopedido` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `versao` integer UNSIGNED NOT NULL CHECK (`versao` >= 0), `descricao` longtext NOT NULL, `status_anterior` varchar(25) NOT NULL, `status_novo` varchar(25) NOT NULL, `criado_em` datetime(6) NOT NULL, `pedido_id` bigint NOT NULL, `responsavel_id` bigint NULL);
--
-- Create model AnexoSolicitacao
--
CREATE TABLE `suprimentos_anexosolicitacao` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `arquivo` varchar(100) NOT NULL, `descricao` varchar(255) NOT NULL, `criado_em` datetime(6) NOT NULL, `enviado_por_id` bigint NULL, `solicitacao_id` bigint NOT NULL);
--
-- Create model AnexoPedido
--
CREATE TABLE `suprimentos_anexopedido` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `arquivo` varchar(100) NOT NULL, `descricao` varchar(255) NOT NULL, `criado_em` datetime(6) NOT NULL, `enviado_por_id` bigint NULL, `pedido_id` bigint NOT NULL);
--
-- Add field solicitacao_gerada to pedido
--
ALTER TABLE `suprimentos_pedido` ADD COLUMN `solicitacao_gerada_id` bigint NULL UNIQUE , ADD CONSTRAINT `suprimentos_pedido_solicitacao_gerada_i_4da76e3b_fk_supriment` FOREIGN KEY (`solicitacao_gerada_id`) REFERENCES `suprimentos_solicitacaocompra`(`id`);
ALTER TABLE `suprimentos_solicitacaocompra` ADD CONSTRAINT `suprimentos_solicita_aprovador_cotacao_id_ddd9cd89_fk_usuario_u` FOREIGN KEY (`aprovador_cotacao_id`) REFERENCES `usuario_usuario` (`id`);
ALTER TABLE `suprimentos_solicitacaocompra` ADD CONSTRAINT `suprimentos_solicita_aprovador_inicial_id_a83bbf82_fk_usuario_u` FOREIGN KEY (`aprovador_inicial_id`) REFERENCES `usuario_usuario` (`id`);
ALTER TABLE `suprimentos_solicitacaocompra` ADD CONSTRAINT `suprimentos_solicita_aprovador_pedido_id_8ba064a7_fk_usuario_u` FOREIGN KEY (`aprovador_pedido_id`) REFERENCES `usuario_usuario` (`id`);
ALTER TABLE `suprimentos_solicitacaocompra` ADD CONSTRAINT `suprimentos_solicita_comprador_id_5c792973_fk_usuario_u` FOREIGN KEY (`comprador_id`) REFERENCES `usuario_usuario` (`id`);
ALTER TABLE `suprimentos_solicitacaocompra` ADD CONSTRAINT `suprimentos_solicita_contrato_id_e684c23a_fk_supriment` FOREIGN KEY (`contrato_id`) REFERENCES `suprimentos_contrato` (`id`);
ALTER TABLE `suprimentos_solicitacaocompra` ADD CONSTRAINT `suprimentos_solicita_filial_id_be1560fa_fk_usuario_f` FOREIGN KEY (`filial_id`) REFERENCES `usuario_filial` (`id`);
ALTER TABLE `suprimentos_solicitacaocompra` ADD CONSTRAINT `suprimentos_solicita_fornecedor_id_7050eb25_fk_supriment` FOREIGN KEY (`fornecedor_id`) REFERENCES `suprimentos_parceiro` (`id`);
ALTER TABLE `suprimentos_solicitacaocompra` ADD CONSTRAINT `suprimentos_solicita_solicitante_id_39481914_fk_usuario_u` FOREIGN KEY (`solicitante_id`) REFERENCES `usuario_usuario` (`id`);
ALTER TABLE `suprimentos_historicosolicitacao` ADD CONSTRAINT `suprimentos_historic_responsavel_id_c8df6a04_fk_usuario_u` FOREIGN KEY (`responsavel_id`) REFERENCES `usuario_usuario` (`id`);
ALTER TABLE `suprimentos_historicosolicitacao` ADD CONSTRAINT `suprimentos_historic_solicitacao_id_2a1aaf83_fk_supriment` FOREIGN KEY (`solicitacao_id`) REFERENCES `suprimentos_solicitacaocompra` (`id`);
ALTER TABLE `suprimentos_historicopedido` ADD CONSTRAINT `suprimentos_historic_pedido_id_cebb709b_fk_supriment` FOREIGN KEY (`pedido_id`) REFERENCES `suprimentos_pedido` (`id`);
ALTER TABLE `suprimentos_historicopedido` ADD CONSTRAINT `suprimentos_historic_responsavel_id_803ebf96_fk_usuario_u` FOREIGN KEY (`responsavel_id`) REFERENCES `usuario_usuario` (`id`);
ALTER TABLE `suprimentos_anexosolicitacao` ADD CONSTRAINT `suprimentos_anexosol_enviado_por_id_e81bde2b_fk_usuario_u` FOREIGN KEY (`enviado_por_id`) REFERENCES `usuario_usuario` (`id`);
ALTER TABLE `suprimentos_anexosolicitacao` ADD CONSTRAINT `suprimentos_anexosol_solicitacao_id_cbc0f86f_fk_supriment` FOREIGN KEY (`solicitacao_id`) REFERENCES `suprimentos_solicitacaocompra` (`id`);
ALTER TABLE `suprimentos_anexopedido` ADD CONSTRAINT `suprimentos_anexoped_enviado_por_id_b6e6ce6a_fk_usuario_u` FOREIGN KEY (`enviado_por_id`) REFERENCES `usuario_usuario` (`id`);
ALTER TABLE `suprimentos_anexopedido` ADD CONSTRAINT `suprimentos_anexoped_pedido_id_80d4611e_fk_supriment` FOREIGN KEY (`pedido_id`) REFERENCES `suprimentos_pedido` (`id`);
