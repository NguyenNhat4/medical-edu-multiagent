import unittest
from nodes import InterviewerNode, PlannerNode, ContentGeneratorBatchNode

class TestMedicalFlow(unittest.TestCase):
    def test_interviewer_done(self):
        node = InterviewerNode()
        # Mock history that triggers "done" (keyword 'slide')
        history = [{"role": "user", "content": "I need a slide about Heart."}]
        shared = {"history": history}

        action = node.run(shared)

        print(f"Interviewer Action: {action}")
        self.assertEqual(action, "done")
        self.assertIn("requirements", shared)
        self.assertEqual(shared["requirements"]["topic"], "Medical Mock Topic")

    def test_interviewer_ask(self):
        node = InterviewerNode()
        # Mock history that triggers "ask"
        history = []
        shared = {"history": history}

        action = node.run(shared)

        print(f"Interviewer Action: {action}")
        self.assertEqual(action, "ask")
        self.assertIn("last_agent_response", shared)
        self.assertEqual(shared["last_agent_response"]["status"], "ask")

    def test_planner_generator(self):
        # Setup shared state as if Interviewer finished
        shared = {
            "requirements": {
                "topic": "Test Topic",
                "audience": "Students",
                "artifacts": ["lecture", "slide"]
            }
        }

        # Test Planner
        planner = PlannerNode()
        planner.run(shared)
        self.assertIn("plan_outline", shared)
        print("Plan Outline generated.")

        # Test Generator
        generator = ContentGeneratorBatchNode()
        generator.run(shared)
        self.assertIn("generated_content", shared)
        self.assertIn("lecture", shared["generated_content"])
        self.assertIn("slide", shared["generated_content"])
        print("Content generated.")

if __name__ == "__main__":
    unittest.main()
