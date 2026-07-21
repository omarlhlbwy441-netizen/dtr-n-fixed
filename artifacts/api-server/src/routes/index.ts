import { Router, type IRouter } from "express";
import healthRouter from "./health";
import dtrnProxyRouter from "./dtrn-proxy";

const router: IRouter = Router();

router.use(healthRouter);
router.use(dtrnProxyRouter);

export default router;
