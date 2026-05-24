-- MySQL dump 10.13  Distrib 8.0.43, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: dbcetest3
-- ------------------------------------------------------
-- Server version	8.0.43

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Dumping data for table `suprimentos_parceiro`
--

LOCK TABLES `suprimentos_parceiro` WRITE;
/*!40000 ALTER TABLE `suprimentos_parceiro` DISABLE KEYS */;
INSERT INTO `suprimentos_parceiro` (`id`, `razao_social`, `nome_fantasia`, `cnpj`, `inscricao_estadual`, `contato`, `telefone`, `celular`, `email`, `site`, `observacoes`, `eh_fabricante`, `eh_fornecedor`, `ativo`, `endereco_id`, `filial_id`) VALUES (1,'Casa do Epi Ltda','Casa do EPI','03.244.478/0003-17','','Joao','31994778547','','comercial@casadoepi.com.br','http://www.casadoepibh.com.br','',1,1,1,45,2),(2,'Elastobor Borrachas e PlÃ¡sticos LTDA','Elastobor','53.840.542/0002-10','','','11 5525-9744','','atendimento3@elastobor.com.br','https://www.elastobor.com.br/','',1,1,1,47,1);
/*!40000 ALTER TABLE `suprimentos_parceiro` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-18 16:14:09
